"""40 evaluation questions on car_company.db with expected answers.

Each item:
    question                - the manager's question (Hebrew)
    expected_sql_contains   - words that must appear in the generated SQL (case-insensitive)
    expected_row_count_min  - minimum number of rows in the result
    difficulty              - easy / medium / hard
    reference_sql           - (extra) a known-good query; used to sanity-check the dataset
                              and evaluators offline:  python -m evaluation.evaluators --check
"""

DATASET_NAME = "dataanalyst-ai-car-company-40"

EVAL_QUESTIONS = [
    # ------------------------------------------------------------------ easy (14)
    {"question": "כמה לקוחות יש בסך הכל?",
     "expected_sql_contains": ["SELECT", "COUNT", "customers"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS total_customers FROM customers"},
    {"question": "כמה סניפים יש לחברה?",
     "expected_sql_contains": ["SELECT", "COUNT", "branches"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS branches_count FROM branches"},
    {"question": "כמה עובדים יש בחברה?",
     "expected_sql_contains": ["SELECT", "COUNT", "employees"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS employees_count FROM employees"},
    {"question": "כמה רכבים נמכרו בסך הכל?",
     "expected_sql_contains": ["SELECT", "COUNT", "sales"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS cars_sold FROM sales"},
    {"question": "מה סך ההכנסות מכל המכירות?",
     "expected_sql_contains": ["SELECT", "SUM", "final_price", "sales"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT SUM(final_price) AS total_revenue FROM sales"},
    {"question": "באילו ערים יש לנו סניפים?",
     "expected_sql_contains": ["SELECT", "city", "branches"], "expected_row_count_min": 10, "difficulty": "easy",
     "reference_sql": "SELECT city, country FROM branches ORDER BY city"},
    {"question": "מה המחיר הממוצע של רכב שנמכר?",
     "expected_sql_contains": ["SELECT", "AVG", "final_price"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT AVG(final_price) AS avg_sale_price FROM sales"},
    {"question": "אילו מותגי רכב אנחנו מוכרים?",
     "expected_sql_contains": ["SELECT", "DISTINCT", "brand", "vehicles"], "expected_row_count_min": 8, "difficulty": "easy",
     "reference_sql": "SELECT DISTINCT brand FROM vehicles ORDER BY brand"},
    {"question": "כמה לקוחות עסקיים יש לנו?",
     "expected_sql_contains": ["SELECT", "COUNT", "customer_type", "business"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS business_customers FROM customers WHERE customer_type = 'business'"},
    {"question": "מה המשכורת הממוצעת בחברה?",
     "expected_sql_contains": ["SELECT", "AVG", "salary", "employees"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT AVG(salary) AS avg_salary FROM employees"},
    {"question": "מה הרכב היקר ביותר בקטלוג?",
     "expected_sql_contains": ["SELECT", "base_price", "vehicles"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT brand, model, year, base_price FROM vehicles ORDER BY base_price DESC LIMIT 1"},
    {"question": "כמה רכבים יש כרגע במלאי בכל הסניפים יחד?",
     "expected_sql_contains": ["SELECT", "SUM", "quantity", "inventory"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT SUM(quantity) AS total_stock FROM inventory"},
    {"question": "כמה מכירות היו ב-2023?",
     "expected_sql_contains": ["SELECT", "COUNT", "sales", "2023"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS sales_2023 FROM sales WHERE strftime('%Y', sale_date) = '2023'"},
    {"question": "כמה לקוחות יש מישראל?",
     "expected_sql_contains": ["SELECT", "COUNT", "customers", "Israel"], "expected_row_count_min": 1, "difficulty": "easy",
     "reference_sql": "SELECT COUNT(*) AS israeli_customers FROM customers WHERE country = 'Israel'"},

    # ------------------------------------------------------------------ medium (14)
    {"question": "מי 5 העובדים עם הכי הרבה מכירות?",
     "expected_sql_contains": ["SELECT", "employees", "sales", "GROUP BY", "LIMIT 5"], "expected_row_count_min": 5, "difficulty": "medium",
     "reference_sql": "SELECT e.first_name, e.last_name, COUNT(*) AS cars_sold FROM sales s JOIN employees e ON e.id = s.employee_id GROUP BY e.id ORDER BY cars_sold DESC LIMIT 5"},
    {"question": "כמה רכבים נמכרו בכל סניף?",
     "expected_sql_contains": ["SELECT", "COUNT", "branches", "GROUP BY"], "expected_row_count_min": 10, "difficulty": "medium",
     "reference_sql": "SELECT b.city, COUNT(*) AS cars_sold FROM sales s JOIN branches b ON b.id = s.branch_id GROUP BY b.id ORDER BY cars_sold DESC"},
    {"question": "מה ההכנסה הכוללת לפי קטגוריית רכב?",
     "expected_sql_contains": ["SELECT", "SUM", "category", "GROUP BY"], "expected_row_count_min": 5, "difficulty": "medium",
     "reference_sql": "SELECT v.category, SUM(s.final_price) AS total_revenue FROM sales s JOIN vehicles v ON v.id = s.vehicle_id GROUP BY v.category ORDER BY total_revenue DESC"},
    {"question": "איזה סניף הכניס הכי הרבה כסף ב-2024?",
     "expected_sql_contains": ["SELECT", "SUM", "final_price", "branches", "2024"], "expected_row_count_min": 1, "difficulty": "medium",
     "reference_sql": "SELECT b.city, SUM(s.final_price) AS revenue FROM sales s JOIN branches b ON b.id = s.branch_id WHERE strftime('%Y', s.sale_date) = '2024' GROUP BY b.id ORDER BY revenue DESC LIMIT 1"},
    {"question": "מה התפלגות אמצעי התשלום במכירות?",
     "expected_sql_contains": ["SELECT", "payment_method", "COUNT", "GROUP BY"], "expected_row_count_min": 3, "difficulty": "medium",
     "reference_sql": "SELECT payment_method, COUNT(*) AS sales_count FROM sales GROUP BY payment_method"},
    {"question": "מה המשכורת הממוצעת לפי תפקיד?",
     "expected_sql_contains": ["SELECT", "AVG", "salary", "role", "GROUP BY"], "expected_row_count_min": 4, "difficulty": "medium",
     "reference_sql": "SELECT role, AVG(salary) AS avg_salary FROM employees GROUP BY role ORDER BY avg_salary DESC"},
    {"question": "כמה רכבים נמכרו מכל מותג?",
     "expected_sql_contains": ["SELECT", "brand", "COUNT", "GROUP BY"], "expected_row_count_min": 8, "difficulty": "medium",
     "reference_sql": "SELECT v.brand, COUNT(*) AS cars_sold FROM sales s JOIN vehicles v ON v.id = s.vehicle_id GROUP BY v.brand ORDER BY cars_sold DESC"},
    {"question": "מה סך המכירות בכל שנה?",
     "expected_sql_contains": ["SELECT", "SUM", "sale_date", "GROUP BY"], "expected_row_count_min": 5, "difficulty": "medium",
     "reference_sql": "SELECT strftime('%Y', sale_date) AS year, COUNT(*) AS cars_sold, SUM(final_price) AS revenue FROM sales GROUP BY year ORDER BY year"},
    {"question": "מי 10 הלקוחות שקנו הכי הרבה רכבים?",
     "expected_sql_contains": ["SELECT", "customers", "COUNT", "GROUP BY", "LIMIT 10"], "expected_row_count_min": 10, "difficulty": "medium",
     "reference_sql": "SELECT c.first_name, c.last_name, COUNT(*) AS cars_bought FROM sales s JOIN customers c ON c.id = s.customer_id GROUP BY c.id ORDER BY cars_bought DESC LIMIT 10"},
    {"question": "כמה לקוחות יש בכל מדינה?",
     "expected_sql_contains": ["SELECT", "country", "COUNT", "customers", "GROUP BY"], "expected_row_count_min": 10, "difficulty": "medium",
     "reference_sql": "SELECT country, COUNT(*) AS customers_count FROM customers GROUP BY country ORDER BY customers_count DESC"},
    {"question": "כמה מלאי יש בכל סניף?",
     "expected_sql_contains": ["SELECT", "SUM", "quantity", "inventory", "GROUP BY"], "expected_row_count_min": 10, "difficulty": "medium",
     "reference_sql": "SELECT b.city, SUM(i.quantity) AS total_stock FROM inventory i JOIN branches b ON b.id = i.branch_id GROUP BY b.id ORDER BY total_stock DESC"},
    {"question": "מה ההנחה הממוצעת או התוספת מהמחיר הבסיסי לפי מותג?",
     "expected_sql_contains": ["SELECT", "AVG", "final_price", "base_price", "brand", "GROUP BY"], "expected_row_count_min": 8, "difficulty": "medium",
     "reference_sql": "SELECT v.brand, AVG(s.final_price - v.base_price) AS avg_diff FROM sales s JOIN vehicles v ON v.id = s.vehicle_id GROUP BY v.brand"},
    {"question": "מה מספר המכירות של רכבים חשמליים בכל שנה?",
     "expected_sql_contains": ["SELECT", "COUNT", "Electric", "GROUP BY"], "expected_row_count_min": 5, "difficulty": "medium",
     "reference_sql": "SELECT strftime('%Y', s.sale_date) AS year, COUNT(*) AS electric_sold FROM sales s JOIN vehicles v ON v.id = s.vehicle_id WHERE v.category = 'Electric' GROUP BY year ORDER BY year"},
    {"question": "השווה מכירות בין המדינות",
     "expected_sql_contains": ["SELECT", "country", "SUM", "GROUP BY"], "expected_row_count_min": 10, "difficulty": "medium",
     "reference_sql": "SELECT b.country, COUNT(*) AS cars_sold, SUM(s.final_price) AS revenue FROM sales s JOIN branches b ON b.id = s.branch_id GROUP BY b.country ORDER BY revenue DESC"},

    # ------------------------------------------------------------------ hard (12)
    {"question": "מה אחוז הצמיחה במכירות לפי רבעון ב-2023 לעומת 2022?",
     "expected_sql_contains": ["SELECT", "sale_date", "2022", "2023", "SUM"], "expected_row_count_min": 4, "difficulty": "hard",
     "reference_sql": """WITH q AS (
        SELECT strftime('%Y', sale_date) AS year, (CAST(strftime('%m', sale_date) AS INTEGER) + 2) / 3 AS quarter,
               SUM(final_price) AS revenue
        FROM sales WHERE strftime('%Y', sale_date) IN ('2022', '2023') GROUP BY year, quarter)
        SELECT a.quarter, a.revenue AS revenue_2022, b.revenue AS revenue_2023,
               ROUND(100.0 * (b.revenue - a.revenue) / a.revenue, 1) AS growth_pct
        FROM q a JOIN q b ON a.quarter = b.quarter AND a.year = '2022' AND b.year = '2023' ORDER BY a.quarter"""},
    {"question": "מי העובד שמכר הכי הרבה רכבים ב-2024?",
     "expected_sql_contains": ["SELECT", "employees", "COUNT", "2024", "GROUP BY"], "expected_row_count_min": 1, "difficulty": "hard",
     "reference_sql": "SELECT e.first_name, e.last_name, COUNT(*) AS cars_sold FROM sales s JOIN employees e ON e.id = s.employee_id WHERE strftime('%Y', s.sale_date) = '2024' GROUP BY e.id ORDER BY cars_sold DESC LIMIT 1"},
    {"question": "מה הרכב הנמכר ביותר לפי קטגוריה?",
     "expected_sql_contains": ["SELECT", "category", "model", "COUNT", "GROUP BY"], "expected_row_count_min": 5, "difficulty": "hard",
     "reference_sql": """WITH m AS (SELECT v.category, v.brand, v.model, COUNT(*) AS cars_sold
        FROM sales s JOIN vehicles v ON v.id = s.vehicle_id GROUP BY v.category, v.brand, v.model),
        r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY cars_sold DESC) AS rn FROM m)
        SELECT category, brand, model, cars_sold FROM r WHERE rn = 1"""},
    {"question": "מה המגמה החודשית של המכירות ב-3 שנים האחרונות?",
     "expected_sql_contains": ["SELECT", "strftime", "sale_date", "GROUP BY"], "expected_row_count_min": 24, "difficulty": "hard",
     "reference_sql": "SELECT strftime('%Y-%m', sale_date) AS month, COUNT(*) AS cars_sold, SUM(final_price) AS revenue FROM sales WHERE sale_date >= '2022-01-01' GROUP BY month ORDER BY month"},
    {"question": "איזה עובד הכניס הכי הרבה כסף בכל סניף?",
     "expected_sql_contains": ["SELECT", "employees", "branches", "SUM", "GROUP BY"], "expected_row_count_min": 10, "difficulty": "hard",
     "reference_sql": """WITH t AS (SELECT b.city, e.first_name, e.last_name, SUM(s.final_price) AS revenue
        FROM sales s JOIN employees e ON e.id = s.employee_id JOIN branches b ON b.id = e.branch_id GROUP BY e.id),
        r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY city ORDER BY revenue DESC) AS rn FROM t)
        SELECT city, first_name, last_name, revenue FROM r WHERE rn = 1"""},
    {"question": "מה אחוז ההכנסות של כל סניף מסך ההכנסות של החברה?",
     "expected_sql_contains": ["SELECT", "SUM", "final_price", "branches", "GROUP BY"], "expected_row_count_min": 10, "difficulty": "hard",
     "reference_sql": "SELECT b.city, SUM(s.final_price) AS revenue, ROUND(100.0 * SUM(s.final_price) / (SELECT SUM(final_price) FROM sales), 1) AS revenue_pct FROM sales s JOIN branches b ON b.id = s.branch_id GROUP BY b.id ORDER BY revenue DESC"},
    {"question": "אילו דגמים לא נמכרו בכלל ב-2024?",
     "expected_sql_contains": ["SELECT", "model", "vehicles", "2024"], "expected_row_count_min": 1, "difficulty": "hard",
     "reference_sql": """SELECT DISTINCT v.brand, v.model FROM vehicles v
        WHERE (v.brand, v.model) NOT IN (SELECT v2.brand, v2.model FROM sales s JOIN vehicles v2 ON v2.id = s.vehicle_id
                                        WHERE strftime('%Y', s.sale_date) = '2024')"""},
    {"question": "מה ההכנסה הממוצעת לעובד בכל תפקיד?",
     "expected_sql_contains": ["SELECT", "role", "SUM", "employees", "GROUP BY"], "expected_row_count_min": 2, "difficulty": "hard",
     "reference_sql": """SELECT e.role, SUM(s.final_price) * 1.0 / COUNT(DISTINCT e.id) AS revenue_per_employee
        FROM sales s JOIN employees e ON e.id = s.employee_id GROUP BY e.role"""},
    {"question": "מה הדירוג של המותגים לפי הכנסות בכל שנה?",
     "expected_sql_contains": ["SELECT", "brand", "SUM", "GROUP BY"], "expected_row_count_min": 30, "difficulty": "hard",
     "reference_sql": """SELECT strftime('%Y', s.sale_date) AS year, v.brand, SUM(s.final_price) AS revenue,
               RANK() OVER (PARTITION BY strftime('%Y', s.sale_date) ORDER BY SUM(s.final_price) DESC) AS brand_rank
        FROM sales s JOIN vehicles v ON v.id = s.vehicle_id GROUP BY year, v.brand ORDER BY year, brand_rank"""},
    {"question": "מה ההבדל בממוצע מחיר המכירה בין לקוחות פרטיים לעסקיים בכל קטגוריה?",
     "expected_sql_contains": ["SELECT", "AVG", "customer_type", "category", "GROUP BY"], "expected_row_count_min": 5, "difficulty": "hard",
     "reference_sql": """SELECT v.category, c.customer_type, AVG(s.final_price) AS avg_price
        FROM sales s JOIN vehicles v ON v.id = s.vehicle_id JOIN customers c ON c.id = s.customer_id
        GROUP BY v.category, c.customer_type ORDER BY v.category"""},
    {"question": "באיזה חודש בשנה יש בממוצע הכי הרבה מכירות?",
     "expected_sql_contains": ["SELECT", "strftime", "COUNT", "GROUP BY"], "expected_row_count_min": 1, "difficulty": "hard",
     "reference_sql": """SELECT strftime('%m', sale_date) AS month, COUNT(*) * 1.0 / COUNT(DISTINCT strftime('%Y', sale_date)) AS avg_sales
        FROM sales GROUP BY month ORDER BY avg_sales DESC"""},
    {"question": "אילו סניפים מחזיקים במלאי של יותר מ-20 רכבים חשמליים?",
     "expected_sql_contains": ["SELECT", "SUM", "quantity", "Electric", "HAVING"], "expected_row_count_min": 1, "difficulty": "hard",
     "reference_sql": """SELECT b.city, SUM(i.quantity) AS electric_stock FROM inventory i
        JOIN vehicles v ON v.id = i.vehicle_id JOIN branches b ON b.id = i.branch_id
        WHERE v.category = 'Electric' GROUP BY b.id HAVING SUM(i.quantity) > 20 ORDER BY electric_stock DESC"""},
]

assert len(EVAL_QUESTIONS) == 40, len(EVAL_QUESTIONS)
