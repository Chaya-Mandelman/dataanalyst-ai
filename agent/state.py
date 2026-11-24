"""AgentState - the shared state that flows between the LangGraph nodes."""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str           # שאלת המנהל
    sql_query: str          # שאילתה שנוצרה
    sql_explanation: str    # הסבר בעברית פשוטה מה השאילתה עושה
    is_safe: bool           # עברה בדיקת SELECT בלבד
    safety_msg: str         # הסבר אם לא בטוח
    approved: bool          # אישור המנהל
    results: Any            # DataFrame עם תוצאות
    error: str              # הודעת שגיאה
    retry_count: int        # ספירת ניסיונות תיקון (מקס 3)
    chart_types: list[str]  # 3 סוגי גרפים שנבחרו
    insights: str           # תובנות מילוליות

    # --- Extra bookkeeping fields (not part of the original spec) ---
    safety_retries: int     # כמה פעמים ה-generator יצר SQL לא בטוח (מקס 3)
    final_response: dict    # התשובה הסופית שמוצגת ב-UI


MAX_RETRIES = 3


def initial_state(question: str) -> AgentState:
    """A clean state for a new question."""
    return AgentState(
        question=question,
        sql_query="",
        sql_explanation="",
        is_safe=False,
        safety_msg="",
        approved=False,
        results=None,
        error="",
        retry_count=0,
        chart_types=[],
        insights="",
        safety_retries=0,
        final_response={},
    )
