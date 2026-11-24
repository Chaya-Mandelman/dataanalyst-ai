"""Safe, read-only access to car_company.db.

Three layers of protection:
  1. check_sql_safety() - Python regex check (SELECT/WITH only, no write keywords, one statement).
  2. The connection is opened with SQLite URI mode=ro (read-only at the file level).
  3. PRAGMA query_only=ON + a time limit, so even a slipped statement can't write or hang.
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "car_company.db"

MAX_ROWS = 5000          # results are capped so the UI and LLM stay responsive
QUERY_TIMEOUT_SEC = 10

# Keywords required by the spec + a few more SQLite statements that can change state.
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX", "GRANT", "REVOKE",
]
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE)
# One pass over the SQL: string literals and comments are matched together, so a
# "--" inside a string isn't mistaken for a comment (and vice versa).
_TOKEN_RE = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|--[^\n]*|/\*.*?(?:\*/|$)", re.DOTALL)
_FENCE_RE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE)


def clean_sql(sql: str) -> str:
    """Strip markdown fences / whitespace / trailing semicolons the LLM may add."""
    sql = _FENCE_RE.sub("", (sql or "").strip()).strip()
    return sql.rstrip(";").strip()


def check_sql_safety(sql: str) -> tuple[bool, str]:
    """Code-level safety check. Returns (is_safe, hebrew_message)."""
    sql = clean_sql(sql)
    if not sql:
        return False, "לא נוצרה שאילתה."

    # Remove comments (they could hide a second statement) and string literals
    # (so a value like WHERE color = 'Update' isn't a false positive).
    code_no_strings = _TOKEN_RE.sub(lambda m: "''" if m.group(0)[0] in "'\"" else " ", sql)

    found = sorted({m.group(1).upper() for m in _FORBIDDEN_RE.finditer(code_no_strings)})
    if found:
        return False, f"השאילתה מכילה פקודות אסורות שמשנות נתונים: {', '.join(found)}. מותרות רק שאילתות קריאה (SELECT)."

    if ";" in code_no_strings.strip().rstrip(";"):
        return False, "השאילתה מכילה יותר מפקודה אחת. מותרת פקודת SELECT אחת בלבד."

    first_word = code_no_strings.strip().split(None, 1)[0].upper() if code_no_strings.strip() else ""
    if first_word not in ("SELECT", "WITH"):
        return False, f"השאילתה מתחילה ב-{first_word} ולא ב-SELECT. מותרות רק שאילתות קריאה."

    return True, "השאילתה עברה את בדיקת הבטיחות (קריאה בלבד)."


def get_readonly_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the DB in read-only mode: sqlite3.connect("file:car_company.db?mode=ro", uri=True).

    Path.as_uri() percent-encodes the absolute path, so folders with spaces or
    non-ASCII (e.g. Hebrew) names work.
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}. Run database/create_db.py first.")
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("PRAGMA query_only = ON")
    return conn


def run_query(sql: str, db_path: Path = DB_PATH, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    """Run a SELECT query safely and return a DataFrame. Raises on unsafe SQL or SQLite errors."""
    is_safe, msg = check_sql_safety(sql)
    if not is_safe:
        raise PermissionError(msg)

    conn = get_readonly_connection(db_path)
    deadline = time.monotonic() + QUERY_TIMEOUT_SEC
    # Returning non-zero from the progress handler aborts the query (-> sqlite3.OperationalError).
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
    try:
        cur = conn.execute(clean_sql(sql))
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows)
        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()
