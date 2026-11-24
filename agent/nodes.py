"""The 7 LangGraph nodes of DataAnalyst AI.

All LLM calls go through GPT-4o-mini (see get_llm). The LLM helper functions
(_llm_*) are kept separate from the node functions so each node can be tested
on its own (and the LLM can be mocked in tests).
"""

import os
import re
from functools import lru_cache

import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agent import prompts
from agent.state import MAX_RETRIES, AgentState
from database.executor import check_sql_safety, clean_sql, run_query

LLM_MODEL = "gpt-4o-mini"
ALL_CHART_TYPES = ["bar", "line", "pie", "histogram", "scatter", "heatmap"]


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

class SQLResponse(BaseModel):
    sql_query: str = Field(description="A single read-only SQLite SELECT query")
    sql_explanation: str = Field(description="הסבר קצר בעברית פשוטה מה השאילתה עושה")


class FixedSQL(BaseModel):
    sql_query: str = Field(description="The corrected read-only SQLite SELECT query")


@lru_cache(maxsize=1)
def get_llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=LLM_MODEL, temperature=0)


def get_prompt_version(config: RunnableConfig | None) -> str:
    configurable = (config or {}).get("configurable", {})
    return configurable.get("prompt_version") or os.getenv("PROMPT_VERSION", "improved")


def _llm_generate_sql(question: str, version: str, feedback: str = "") -> SQLResponse:
    messages = [SystemMessage(prompts.sql_generator_system_prompt(version)), HumanMessage(question)]
    if feedback:
        messages.append(HumanMessage(feedback))
    return get_llm().with_structured_output(SQLResponse).invoke(messages)


def _llm_fix_sql(question: str, sql_query: str, error: str) -> FixedSQL:
    messages = [
        SystemMessage(prompts.ERROR_FIXER_SYSTEM_PROMPT),
        HumanMessage(prompts.ERROR_FIXER_USER_TEMPLATE.format(question=question, sql_query=sql_query, error=error)),
    ]
    return get_llm().with_structured_output(FixedSQL).invoke(messages)


def _llm_insights(question: str, sql_explanation: str, df: pd.DataFrame, max_rows: int = 40) -> str:
    shown = min(len(df), max_rows)
    messages = [
        SystemMessage(prompts.INSIGHTS_SYSTEM_PROMPT),
        HumanMessage(prompts.INSIGHTS_USER_TEMPLATE.format(
            question=question,
            sql_explanation=sql_explanation,
            row_count=len(df),
            shown=shown,
            table=df.head(max_rows).to_csv(index=False),
        )),
    ]
    result: AIMessage = get_llm().invoke(messages)
    return str(result.content).strip()


# ---------------------------------------------------------------------------
# Node 1: sql_generator
# ---------------------------------------------------------------------------

def sql_generator(state: AgentState, config: RunnableConfig | None = None) -> dict:
    """Question + fixed schema -> sql_query + sql_explanation (Hebrew)."""
    feedback = ""
    if state.get("sql_query") and state.get("is_safe") is False and state.get("safety_msg"):
        # We are here because the validator rejected the previous attempt.
        feedback = prompts.SAFETY_FEEDBACK_TEMPLATE.format(
            safety_msg=state["safety_msg"], sql_query=state["sql_query"]
        )
    resp = _llm_generate_sql(state["question"], get_prompt_version(config), feedback)
    return {
        "sql_query": clean_sql(resp.sql_query),
        "sql_explanation": resp.sql_explanation.strip(),
        "error": "",
    }


# ---------------------------------------------------------------------------
# Node 2: sql_validator  (code-level check, not just a prompt)
# ---------------------------------------------------------------------------

def sql_validator(state: AgentState) -> dict:
    is_safe, msg = check_sql_safety(state.get("sql_query", ""))
    update: dict = {"is_safe": is_safe, "safety_msg": "" if is_safe else msg}
    if not is_safe:
        retries = state.get("safety_retries", 0) + 1
        update["safety_retries"] = retries
        if retries >= MAX_RETRIES:
            update["error"] = f"הסוכן לא הצליח לייצר שאילתה בטוחה אחרי {MAX_RETRIES} ניסיונות. {msg}"
    return update


# ---------------------------------------------------------------------------
# Node 3: human_approval  (LangGraph interrupt)
# ---------------------------------------------------------------------------

def human_approval(state: AgentState) -> dict:
    """Pause the graph and wait for the manager. Resume with Command(resume=True/False)."""
    decision = interrupt({
        "type": "approval_request",
        "question": state["question"],
        "sql_explanation": state.get("sql_explanation", ""),
        "sql_query": state.get("sql_query", ""),
    })
    if isinstance(decision, dict):
        decision = decision.get("approved", False)
    approved = decision is True or (isinstance(decision, str) and decision.strip().lower() in {"yes", "approve", "true", "כן", "אשר"})
    update: dict = {"approved": approved}
    if not approved:
        update["final_response"] = {"status": "cancelled", "message": "הפעולה בוטלה על ידי המנהל."}
    return update


# ---------------------------------------------------------------------------
# Node 4: sql_executor  (read-only connection)
# ---------------------------------------------------------------------------

def sql_executor(state: AgentState) -> dict:
    try:
        df = run_query(state["sql_query"])
    except Exception as exc:  # sqlite3 errors, safety errors, timeouts
        return {"error": f"{type(exc).__name__}: {exc}", "results": None}
    return {"results": df, "error": ""}


# ---------------------------------------------------------------------------
# Node 5: error_handler  (LLM fixes the SQL; does NOT go back to sql_generator)
# ---------------------------------------------------------------------------

def error_handler(state: AgentState) -> dict:
    retry_count = state.get("retry_count", 0)
    if retry_count >= MAX_RETRIES:
        msg = (f"לא הצלחתי להריץ את השאילתה גם אחרי {MAX_RETRIES} ניסיונות תיקון. "
               f"נסה לנסח את השאלה מחדש. שגיאה אחרונה: {state.get('error', '')}")
        return {"error": msg, "final_response": {"status": "failed", "message": msg}}

    fixed = _llm_fix_sql(state["question"], state["sql_query"], state.get("error", ""))
    fixed_sql = clean_sql(fixed.sql_query)
    update: dict = {"sql_query": fixed_sql, "retry_count": retry_count + 1}

    # The fixed query skips sql_validator, so re-check it here in code.
    is_safe, msg = check_sql_safety(fixed_sql)
    if not is_safe:
        update["error"] = f"התיקון שהוצע נחסם בבדיקת הבטיחות: {msg}"
    return update


# ---------------------------------------------------------------------------
# Node 6: visualization_selector  (rule-based, always exactly 3)
# ---------------------------------------------------------------------------

_DATE_NAME_RE = re.compile(r"(^|_)(date|month|year|quarter|period|week|day)(_|$)|שנה|חודש|רבעון|תאריך", re.IGNORECASE)
_DATE_VALUE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?|-?Q[1-4])?$", re.IGNORECASE)
_ID_NAME_RE = re.compile(r"(^id$|_id$)", re.IGNORECASE)


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Classify columns into date / numeric / categorical."""
    date_cols, numeric_cols, cat_cols = [], [], []
    for col in df.columns:
        s = df[col].dropna()
        name = str(col)
        if _ID_NAME_RE.search(name):
            continue
        sample = s.astype(str).head(50)
        looks_like_date_values = len(sample) > 0 and sample.str.match(_DATE_VALUE_RE).all()
        if _DATE_NAME_RE.search(name) and (looks_like_date_values or pd.api.types.is_numeric_dtype(s)):
            date_cols.append(col)
        elif looks_like_date_values and not pd.api.types.is_numeric_dtype(s):
            date_cols.append(col)
        elif pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            numeric_cols.append(col)
        else:
            cat_cols.append(col)
    n_unique_cat = {c: int(df[c].nunique()) for c in cat_cols}
    return {
        "rows": len(df),
        "date_cols": date_cols,
        "numeric_cols": numeric_cols,
        "cat_cols": cat_cols,
        "n_unique_cat": n_unique_cat,
    }


def choose_chart_types(df: pd.DataFrame | None) -> list[str]:
    """Rules from the spec, in priority order, then padded to exactly 3."""
    if df is None or df.empty:
        return ["bar", "pie", "histogram"]

    p = profile_dataframe(df)
    rows, dates, nums, cats = p["rows"], p["date_cols"], p["numeric_cols"], p["cat_cols"]
    few_cats = [c for c in cats if 1 < p["n_unique_cat"][c] <= 12]
    chosen: list[str] = []

    def add(t: str) -> None:
        if t not in chosen:
            chosen.append(t)

    if dates:                                   # date column -> line is mandatory
        add("line")
    if cats and (nums or rows > 1):             # countable categories -> bar / pie
        add("bar")
        if few_cats and (not nums or (df[nums[0]].dropna() >= 0).all()):
            add("pie")
    if len(nums) >= 2:                          # two continuous values -> scatter
        add("scatter")
    if rows >= 30 and nums:                     # many rows -> histogram
        add("histogram")
    if (len(cats) >= 2 and nums) or (dates and cats and nums) or len(nums) >= 3:
        add("heatmap")

    fallback = ["bar", "line", "histogram", "pie", "scatter", "heatmap"] if dates else \
               ["bar", "pie", "histogram", "scatter", "line", "heatmap"]
    for t in fallback:
        if len(chosen) >= 3:
            break
        add(t)
    return chosen[:3]


def visualization_selector(state: AgentState) -> dict:
    return {"chart_types": choose_chart_types(state.get("results"))}


# ---------------------------------------------------------------------------
# Node 7: response_generator
# ---------------------------------------------------------------------------

def response_generator(state: AgentState) -> dict:
    df = state.get("results")
    if df is None or df.empty:
        insights = "השאילתה רצה בהצלחה אבל לא החזירה תוצאות. ייתכן שאין נתונים שעונים על התנאים בשאלה."
    else:
        try:
            insights = _llm_insights(state["question"], state.get("sql_explanation", ""), df)
        except Exception as exc:
            insights = f"התוצאות מוכנות, אך לא ניתן היה להפיק תובנות מילוליות ({type(exc).__name__})."
    return {
        "insights": insights,
        "final_response": {
            "status": "success",
            "question": state["question"],
            "sql_query": state.get("sql_query", ""),
            "sql_explanation": state.get("sql_explanation", ""),
            "row_count": 0 if df is None else len(df),
            "chart_types": state.get("chart_types", []),
            "insights": insights,
            "retry_count": state.get("retry_count", 0),
        },
    }
