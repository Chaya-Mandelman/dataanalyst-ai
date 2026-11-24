"""LangSmith evaluation: Experiment A (baseline prompt) vs Experiment B (improved prompt).

Usage (from the project root):
    python -m evaluation.evaluators              # Experiment A + B on LangSmith (results stay in LangSmith)
    python -m evaluation.evaluators --check      # offline: score the reference SQL (should be 1.0)

What is evaluated: the SQL-generation step (sql_generator + code safety check),
executed read-only against car_company.db - no human approval and no automatic
error fixing, so the score reflects the prompt itself.
"""

import argparse
import re
import sys
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

from agent.nodes import _llm_generate_sql  # noqa: E402
from database.executor import check_sql_safety, clean_sql, run_query  # noqa: E402
from evaluation.dataset import DATASET_NAME, EVAL_QUESTIONS  # noqa: E402

METRICS = ["sql_executes_successfully", "has_results", "sql_contains_expected"]


# ---------------------------------------------------------------------------
# Target: question -> SQL -> execute
# ---------------------------------------------------------------------------

def execute_sql(sql: str) -> dict:
    out = {"sql_query": sql, "executed": False, "row_count": 0, "error": ""}
    is_safe, msg = check_sql_safety(sql)
    if not is_safe:
        out["error"] = f"unsafe: {msg}"
        return out
    try:
        df = run_query(sql)
        out.update(executed=True, row_count=len(df))
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def make_target(prompt_version: str):
    def target(inputs: dict) -> dict:
        try:
            resp = _llm_generate_sql(inputs["question"], prompt_version)
            sql = clean_sql(resp.sql_query)
        except Exception as exc:
            return {"sql_query": "", "executed": False, "row_count": 0, "error": f"LLM error: {exc}"}
        return execute_sql(sql)

    target.__name__ = f"sql_agent_{prompt_version}"
    return target


# ---------------------------------------------------------------------------
# The 3 evaluators (LangSmith signature: run, example)
# ---------------------------------------------------------------------------

def _outputs(obj) -> dict:
    return (getattr(obj, "outputs", None) or {}) if not isinstance(obj, dict) else obj


def sql_executes_successfully(run, example) -> dict:
    """1 if the SQL ran without an error, else 0."""
    out = _outputs(run)
    return {"key": "sql_executes_successfully", "score": int(bool(out.get("executed"))),
            "comment": out.get("error") or "ok"}


def has_results(run, example) -> dict:
    """1 if the result has at least one row, else 0."""
    out = _outputs(run)
    return {"key": "has_results", "score": int(out.get("row_count", 0) >= 1),
            "comment": f"rows={out.get('row_count', 0)}"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def sql_contains_expected(run, example) -> dict:
    """Fraction (0..1) of expected words found in the SQL (case/whitespace-insensitive)."""
    sql = _normalize(_outputs(run).get("sql_query", ""))
    expected = _outputs(example).get("expected_sql_contains", [])
    if not expected:
        return {"key": "sql_contains_expected", "score": 1.0}
    found = [w for w in expected if _normalize(w) in sql]
    missing = [w for w in expected if w not in found]
    return {"key": "sql_contains_expected", "score": round(len(found) / len(expected), 3),
            "comment": "missing: " + ", ".join(missing) if missing else "all found"}


EVALUATORS = [sql_executes_successfully, has_results, sql_contains_expected]


# ---------------------------------------------------------------------------
# Dataset + experiments
# ---------------------------------------------------------------------------

def _example_outputs(item: dict) -> dict:
    return {k: item[k] for k in ("expected_sql_contains", "expected_row_count_min", "difficulty")}


def ensure_langsmith_dataset(client):
    if client.has_dataset(dataset_name=DATASET_NAME):
        return client.read_dataset(dataset_name=DATASET_NAME)
    ds = client.create_dataset(DATASET_NAME, description="40 Hebrew questions on car_company.db (Text-to-SQL)")
    examples = [{"inputs": {"question": q["question"]}, "outputs": _example_outputs(q),
                 "metadata": {"difficulty": q["difficulty"]}} for q in EVAL_QUESTIONS]
    try:  # langsmith >= 0.3
        client.create_examples(dataset_id=ds.id, examples=examples)
    except TypeError:  # older langsmith
        client.create_examples(inputs=[e["inputs"] for e in examples], outputs=[e["outputs"] for e in examples],
                               metadata=[e["metadata"] for e in examples], dataset_id=ds.id)
    return ds


def run_langsmith_experiment(prompt_version: str, label: str) -> dict:
    from langsmith import Client, evaluate

    client = Client()
    ensure_langsmith_dataset(client)
    results = evaluate(
        make_target(prompt_version),
        data=DATASET_NAME,
        evaluators=EVALUATORS,
        experiment_prefix=f"{label}-{prompt_version}",
        description=f"{label}: sql_generator with the '{prompt_version}' prompt",
        metadata={"prompt_version": prompt_version, "model": "gpt-4o-mini"},
        max_concurrency=4,
        client=client,
    )
    rows = []
    for r in results:
        scores = {e.key: e.score for e in r["evaluation_results"]["results"]}
        rows.append({"difficulty": (r["example"].outputs or {}).get("difficulty", "?"), **scores})
    return {"rows": rows, "experiment": getattr(results, "experiment_name", label)}


def summarize(rows: list[dict]) -> dict:
    def avg(subset, m):
        vals = [r.get(m) for r in subset if r.get(m) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    summary = {"overall": {m: avg(rows, m) for m in METRICS}}
    for d in ("easy", "medium", "hard"):
        subset = [r for r in rows if r["difficulty"] == d]
        summary[d] = {m: avg(subset, m) for m in METRICS}
    return summary


def print_comparison(a: dict, b: dict) -> None:
    """Short A vs B summary in the terminal. The full results live in LangSmith."""
    sa, sb = summarize(a["rows"]), summarize(b["rows"])
    print()
    print(f"Experiment A: {a['experiment']}  (baseline prompt)")
    print(f"Experiment B: {b['experiment']}  (improved prompt)")
    print()
    print(f"{'scope':<8} {'metric':<28} {'A':>7} {'B':>7} {'Δ B-A':>8}")
    for scope in ("overall", "easy", "medium", "hard"):
        for m in METRICS:
            va, vb = sa[scope][m], sb[scope][m]
            print(f"{scope:<8} {m:<28} {va:>7.3f} {vb:>7.3f} {vb - va:>+8.3f}")
    print()
    print(f"Full results: LangSmith > Datasets & Experiments > {DATASET_NAME} > "
          "select both experiments > Compare")


def check_reference() -> int:
    """Offline sanity check (no LLM, no LangSmith): every question's reference SQL
    must run, return >= expected_row_count_min rows and score 1.0 on all evaluators."""
    bad = 0
    for q in EVAL_QUESTIONS:
        out = execute_sql(q["reference_sql"])
        run, example = SimpleNamespace(outputs=out), SimpleNamespace(outputs=_example_outputs(q))
        scores = {ev.__name__: ev(run, example)["score"] for ev in EVALUATORS}
        if not all(v == 1 for v in scores.values()) or out["row_count"] < q["expected_row_count_min"]:
            bad += 1
            print(f"FAIL [{q['difficulty']}] {q['question']}: {scores} rows={out['row_count']} "
                  f"min={q['expected_row_count_min']} {out['error']}")
    print(f"reference check: {len(EVAL_QUESTIONS) - bad}/{len(EVAL_QUESTIONS)} questions pass")
    return bad


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="offline check of dataset + evaluators")
    args = parser.parse_args()

    if args.check:
        sys.exit(1 if check_reference() else 0)

    a = run_langsmith_experiment("baseline", "A")
    b = run_langsmith_experiment("improved", "B")
    print_comparison(a, b)


if __name__ == "__main__":
    main()
