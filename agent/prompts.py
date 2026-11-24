"""Prompts and the fixed database schema used by the agent.

Two prompt versions exist for the LangSmith A/B experiment:
  * "baseline" - schema only (Experiment A)
  * "improved" - schema + value hints + rules + few-shot SQL examples (Experiment B)
The app uses "improved" by default (override with env var PROMPT_VERSION).
"""

SCHEMA = """\
טבלאות: branches, employees, customers, vehicles, sales, inventory
branches: id, city, country, opened_date
employees: id, first_name, last_name, role, branch_id, hire_date, salary
customers: id, first_name, last_name, country, city, customer_type, join_date
vehicles: id, brand, model, year, category, base_price, color
sales: id, vehicle_id, customer_id, employee_id, branch_id, sale_date, final_price, payment_method
inventory: id, vehicle_id, branch_id, quantity, last_updated
"""

# Extra knowledge about the data - only the improved prompt gets it.
SCHEMA_DETAILS = """\
Relationships (foreign keys):
- employees.branch_id -> branches.id
- sales.vehicle_id -> vehicles.id, sales.customer_id -> customers.id,
  sales.employee_id -> employees.id, sales.branch_id -> branches.id
- inventory.vehicle_id -> vehicles.id, inventory.branch_id -> branches.id

Value notes (all stored values are in ENGLISH - translate Hebrew terms):
- Dates are TEXT in 'YYYY-MM-DD' format. Use strftime('%Y', sale_date), strftime('%Y-%m', sale_date) etc.
- Sales data covers 2020-01 to 2024-12. "השנה" / this year = 2024, "שנה שעברה" / last year = 2023,
  "3 השנים האחרונות" = 2022-2024.
- branches: one branch per country. city/country values: Tel Aviv/Israel, New York/USA, London/UK,
  Paris/France, Berlin/Germany, Tokyo/Japan, Dubai/UAE, Sao Paulo/Brazil, Sydney/Australia, Toronto/Canada.
- customers.country also includes Spain, Italy, Mexico (served by the Paris / New York branches).
- employees.role: 'Branch Manager', 'Sales Manager', 'Sales Rep', 'Finance Advisor'. salary is yearly USD.
- customers.customer_type: 'private' or 'business'.
- vehicles: one row per model per model-year (2018-2024). brand: Toyota, BMW, Mercedes, Tesla, Ford,
  Honda, Audi, Volvo. category: 'Sedan', 'SUV', 'Truck', 'Electric', 'Luxury'. base_price in USD.
  A "model" (e.g. 'RAV4') appears in several rows - group by brand, model to count a model's sales.
- sales.final_price is the actual revenue in USD. payment_method: 'cash', 'finance', 'lease'.
- inventory.quantity = current stock of a vehicle at a branch.
- "מדינות" in a sales context usually means the branch country (branches.country).
"""

FEW_SHOT_EXAMPLES = """\
Example 1
Question: כמה רכבים נמכרו בכל סניף?
SQL:
SELECT b.city AS branch_city, b.country, COUNT(*) AS cars_sold
FROM sales s
JOIN branches b ON b.id = s.branch_id
GROUP BY b.id, b.city, b.country
ORDER BY cars_sold DESC;

Example 2
Question: מה ההכנסה החודשית ב-2023?
SQL:
SELECT strftime('%Y-%m', s.sale_date) AS month, SUM(s.final_price) AS revenue, COUNT(*) AS sales_count
FROM sales s
WHERE strftime('%Y', s.sale_date) = '2023'
GROUP BY month
ORDER BY month;

Example 3
Question: מי 3 העובדים שהכניסו הכי הרבה כסף?
SQL:
SELECT e.first_name || ' ' || e.last_name AS employee_name, b.city AS branch_city,
       COUNT(*) AS cars_sold, SUM(s.final_price) AS total_revenue
FROM sales s
JOIN employees e ON e.id = s.employee_id
JOIN branches b ON b.id = e.branch_id
GROUP BY e.id
ORDER BY total_revenue DESC
LIMIT 3;

Example 4
Question: מה הדגם הנמכר ביותר בכל קטגוריה?
SQL:
WITH model_sales AS (
    SELECT v.category, v.brand, v.model, COUNT(*) AS cars_sold
    FROM sales s JOIN vehicles v ON v.id = s.vehicle_id
    GROUP BY v.category, v.brand, v.model
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY cars_sold DESC) AS rn
    FROM model_sales
)
SELECT category, brand, model, cars_sold FROM ranked WHERE rn = 1 ORDER BY cars_sold DESC;
"""

_GENERATOR_RULES = """\
Rules:
- Write ONE SQLite SELECT statement (WITH ... SELECT is allowed). Never modify data.
- Use only the tables and columns listed above.
- Give result columns clear English snake_case aliases (e.g. total_revenue, cars_sold).
- Prefer human-readable columns (names, cities) over raw ids.
- Order results meaningfully. Do not add LIMIT unless the question asks for top-N / "הכי".
- sql_explanation: 1-3 short sentences in simple Hebrew for a non-technical manager, describing
  what data will be fetched and how (no SQL words, no table names).
"""


def sql_generator_system_prompt(version: str = "improved") -> str:
    if version == "baseline":
        return (
            "You are a SQL expert. Convert the manager's question into a SQLite SELECT query "
            "for the car company database.\n\n"
            f"Database schema:\n{SCHEMA}\n"
            "Return the SQL query and a short explanation in simple Hebrew of what the query does."
        )
    return (
        "You are a senior data analyst for an international car company. "
        "The manager asks questions in Hebrew; you translate them into a correct SQLite query.\n\n"
        f"Database schema:\n{SCHEMA}\n{SCHEMA_DETAILS}\n{_GENERATOR_RULES}\n"
        f"Examples of good queries:\n{FEW_SHOT_EXAMPLES}"
    )


SAFETY_FEEDBACK_TEMPLATE = (
    "The previous query you produced was REJECTED by the safety check: {safety_msg}\n"
    "Rejected query:\n{sql_query}\n"
    "Write a read-only SELECT query instead."
)


ERROR_FIXER_SYSTEM_PROMPT = f"""\
You fix broken SQLite queries for a car company database.
You receive the manager's question, the failing SQL and the SQLite error message.
Return a corrected, read-only SELECT query (WITH ... SELECT allowed) that answers the question.

Database schema:
{SCHEMA}
{SCHEMA_DETAILS}
"""

ERROR_FIXER_USER_TEMPLATE = """\
Question: {question}

Failing SQL:
{sql_query}

SQLite error:
{error}
"""


INSIGHTS_SYSTEM_PROMPT = """\
אתה אנליסט נתונים בכיר בחברת רכבים בינלאומית. המנהל שאל שאלה וקיבל טבלת תוצאות.
כתוב 3-4 משפטים של תובנות עסקיות בעברית פשוטה וברורה:
- התחל בתשובה הישירה לשאלה.
- ציין מספרים בולטים (מובילים, פערים, מגמות, אחוזים).
- סיים בהמלצה או תובנה אחת שימושית למנהל.
אל תמציא נתונים שלא מופיעים בטבלה. סכומים הם בדולרים (USD). אל תשתמש בכותרות או ברשימות.
"""

INSIGHTS_USER_TEMPLATE = """\
שאלת המנהל: {question}

מה השאילתה עשתה: {sql_explanation}

סך הכל שורות בתוצאה: {row_count}
התוצאות (עד {shown} שורות ראשונות, בפורמט CSV):
{table}
"""
