"""Build car_company.db - a SQLite database for an international car company.

Uses only the Python standard library. Data is generated with a fixed random
seed so every run produces the same, internally consistent dataset.
"""

import os
import random
import sqlite3
from datetime import date, timedelta

DB_NAME = "car_company.db"
SEED = 42

random.seed(SEED)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

BRANCHES = [
    ("Tel Aviv", "Israel", "2012-03-15"),
    ("New York", "USA", "2008-06-01"),
    ("London", "UK", "2009-09-20"),
    ("Paris", "France", "2011-04-11"),
    ("Berlin", "Germany", "2010-01-25"),
    ("Tokyo", "Japan", "2013-07-08"),
    ("Dubai", "UAE", "2015-11-30"),
    ("Sao Paulo", "Brazil", "2016-02-14"),
    ("Sydney", "Australia", "2014-05-19"),
    ("Toronto", "Canada", "2012-10-03"),
]

# Local first/last names per country, so people look like they belong there.
NAMES = {
    "Israel": (["Noa", "Yosef", "Tamar", "Avi", "Maya", "David", "Shira", "Eitan", "Yael", "Omer"],
               ["Cohen", "Levi", "Mizrahi", "Peretz", "Biton", "Friedman", "Avraham", "Dahan"]),
    "USA": (["James", "Emily", "Michael", "Sarah", "Robert", "Jessica", "William", "Ashley", "John", "Olivia"],
            ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson"]),
    "UK": (["Oliver", "Amelia", "Harry", "Isla", "George", "Ava", "Jack", "Emily", "Charlie", "Sophie"],
           ["Taylor", "Evans", "Thomas", "Roberts", "Walker", "Wright", "Hughes", "Clarke"]),
    "France": (["Louis", "Chloé", "Gabriel", "Léa", "Hugo", "Manon", "Arthur", "Camille", "Jules", "Inès"],
               ["Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Lefebvre", "Girard", "Roux"]),
    "Germany": (["Lukas", "Anna", "Felix", "Lena", "Jonas", "Mia", "Paul", "Hannah", "Leon", "Laura"],
                ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner", "Becker", "Hoffmann"]),
    "Japan": (["Haruto", "Yui", "Sota", "Hina", "Ren", "Aoi", "Yuto", "Sakura", "Kaito", "Mei"],
              ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura"]),
    "UAE": (["Mohammed", "Fatima", "Ahmed", "Mariam", "Omar", "Aisha", "Khalid", "Noura", "Saeed", "Layla"],
            ["Al Mansouri", "Al Nahyan", "Al Maktoum", "Al Suwaidi", "Al Hashimi", "Al Falasi"]),
    "Brazil": (["Miguel", "Julia", "Arthur", "Beatriz", "Pedro", "Larissa", "Lucas", "Mariana", "Rafael", "Gabriela"],
               ["Silva", "Santos", "Oliveira", "Souza", "Costa", "Pereira", "Almeida", "Ferreira"]),
    "Australia": (["Jack", "Charlotte", "Noah", "Olivia", "William", "Ava", "Thomas", "Mia", "Liam", "Grace"],
                  ["Smith", "Jones", "Brown", "Wilson", "Taylor", "Anderson", "Thompson", "White"]),
    "Canada": (["Liam", "Emma", "Noah", "Charlotte", "Ethan", "Chloe", "Benjamin", "Zoe", "Logan", "Abigail"],
               ["Tremblay", "Gagnon", "Roy", "Côté", "MacDonald", "Campbell", "Martin", "Lee"]),
    "Spain": (["Hugo", "Lucía", "Martín", "Sofía", "Pablo", "Martina", "Daniel", "Paula"],
              ["García", "Fernández", "López", "Martínez", "Sánchez", "Pérez"]),
    "Italy": (["Leonardo", "Giulia", "Francesco", "Aurora", "Alessandro", "Sofia", "Lorenzo", "Ginevra"],
              ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano"]),
    "Mexico": (["Santiago", "Valentina", "Mateo", "Regina", "Sebastián", "Camila", "Diego", "Ximena"],
               ["Hernández", "García", "Martínez", "López", "González", "Rodríguez"]),
}

# Customer countries/cities. Branch countries dominate; a few extra markets too.
CUSTOMER_LOCATIONS = {
    "Israel": ["Tel Aviv", "Jerusalem", "Haifa", "Ramat Gan", "Herzliya"],
    "USA": ["New York", "Boston", "Newark", "Philadelphia", "Jersey City"],
    "UK": ["London", "Manchester", "Birmingham", "Oxford", "Brighton"],
    "France": ["Paris", "Lyon", "Versailles", "Lille", "Nantes"],
    "Germany": ["Berlin", "Hamburg", "Potsdam", "Leipzig", "Munich"],
    "Japan": ["Tokyo", "Yokohama", "Kawasaki", "Saitama", "Chiba"],
    "UAE": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
    "Brazil": ["Sao Paulo", "Campinas", "Santos", "Rio de Janeiro"],
    "Australia": ["Sydney", "Newcastle", "Wollongong", "Parramatta"],
    "Canada": ["Toronto", "Mississauga", "Hamilton", "Ottawa"],
    "Spain": ["Madrid", "Barcelona"],
    "Italy": ["Milan", "Rome"],
    "Mexico": ["Mexico City", "Guadalajara"],
}

# Which branch serves customers from a non-branch country.
FOREIGN_MARKET_BRANCH = {"Spain": "Paris", "Italy": "Paris", "Mexico": "New York"}

# (brand, model, category, base price in USD for the newest year)
MODELS = [
    ("Toyota", "Corolla", "Sedan", 23000),
    ("Toyota", "Camry", "Sedan", 28000),
    ("Toyota", "RAV4", "SUV", 31000),
    ("Toyota", "Highlander", "SUV", 39000),
    ("Toyota", "Tacoma", "Truck", 34000),
    ("Toyota", "bZ4X", "Electric", 43000),
    ("BMW", "3 Series", "Sedan", 45000),
    ("BMW", "5 Series", "Luxury", 58000),
    ("BMW", "X5", "SUV", 66000),
    ("BMW", "7 Series", "Luxury", 96000),
    ("BMW", "iX", "Electric", 88000),
    ("Mercedes", "C-Class", "Sedan", 47000),
    ("Mercedes", "E-Class", "Luxury", 59000),
    ("Mercedes", "GLE", "SUV", 63000),
    ("Mercedes", "S-Class", "Luxury", 115000),
    ("Mercedes", "EQS", "Electric", 105000),
    ("Tesla", "Model 3", "Electric", 40000),
    ("Tesla", "Model Y", "Electric", 45000),
    ("Tesla", "Model S", "Electric", 80000),
    ("Tesla", "Model X", "Electric", 90000),
    ("Ford", "Fusion", "Sedan", 24000),
    ("Ford", "Explorer", "SUV", 38000),
    ("Ford", "F-150", "Truck", 42000),
    ("Ford", "Ranger", "Truck", 33000),
    ("Ford", "Mustang Mach-E", "Electric", 46000),
    ("Honda", "Civic", "Sedan", 24000),
    ("Honda", "Accord", "Sedan", 28000),
    ("Honda", "CR-V", "SUV", 31000),
    ("Honda", "Pilot", "SUV", 39000),
    ("Honda", "Ridgeline", "Truck", 40000),
    ("Audi", "A4", "Sedan", 42000),
    ("Audi", "A8", "Luxury", 90000),
    ("Audi", "Q5", "SUV", 46000),
    ("Audi", "Q7", "SUV", 60000),
    ("Audi", "e-tron GT", "Electric", 106000),
    ("Volvo", "S60", "Sedan", 42000),
    ("Volvo", "S90", "Luxury", 56000),
    ("Volvo", "XC60", "SUV", 45000),
    ("Volvo", "XC90", "SUV", 57000),
    ("Volvo", "EX30", "Electric", 36000),
]

COLORS = ["White", "Black", "Silver", "Gray", "Blue", "Red", "Green", "Beige"]
COLOR_WEIGHTS = [25, 22, 15, 15, 9, 8, 3, 3]

# Some models only exist from a certain model year.
MODEL_FIRST_YEAR = {"bZ4X": 2022, "iX": 2022, "EQS": 2022, "Model Y": 2020,
                    "Mustang Mach-E": 2021, "EX30": 2024, "e-tron GT": 2021}
# Ford Fusion was discontinued after 2020.
MODEL_LAST_YEAR = {"Fusion": 2020}

# Relative monthly sales weight: summer peak (Jun-Aug), quieter in winter.
MONTH_WEIGHTS = {1: 0.65, 2: 0.65, 3: 0.85, 4: 0.95, 5: 1.1, 6: 1.45,
                 7: 1.6, 8: 1.5, 9: 1.05, 10: 0.9, 11: 0.8, 12: 0.9}
# Mild yearly growth.
YEAR_WEIGHTS = {2020: 0.8, 2021: 0.95, 2022: 1.0, 2023: 1.1, 2024: 1.15}

# Branch share of sales (bigger markets sell more).
BRANCH_SALES_WEIGHT = {"New York": 1.6, "London": 1.3, "Tokyo": 1.3, "Berlin": 1.1,
                       "Paris": 1.0, "Dubai": 1.0, "Toronto": 0.9, "Sydney": 0.9,
                       "Tel Aviv": 0.8, "Sao Paulo": 0.7}


def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE branches (
    id          INTEGER PRIMARY KEY,
    city        TEXT NOT NULL,
    country     TEXT NOT NULL,
    opened_date TEXT NOT NULL
);

CREATE TABLE employees (
    id         INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name  TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('Sales Manager','Sales Rep','Branch Manager','Finance Advisor')),
    branch_id  INTEGER NOT NULL REFERENCES branches(id),
    hire_date  TEXT NOT NULL,
    salary     INTEGER NOT NULL
);

CREATE TABLE customers (
    id            INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    country       TEXT NOT NULL,
    city          TEXT NOT NULL,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('private','business')),
    join_date     TEXT NOT NULL
);

CREATE TABLE vehicles (
    id         INTEGER PRIMARY KEY,
    brand      TEXT NOT NULL,
    model      TEXT NOT NULL,
    year       INTEGER NOT NULL,
    category   TEXT NOT NULL CHECK (category IN ('Sedan','SUV','Truck','Electric','Luxury')),
    base_price INTEGER NOT NULL,
    color      TEXT NOT NULL
);

CREATE TABLE sales (
    id             INTEGER PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id),
    customer_id    INTEGER NOT NULL REFERENCES customers(id),
    employee_id    INTEGER NOT NULL REFERENCES employees(id),
    branch_id      INTEGER NOT NULL REFERENCES branches(id),
    sale_date      TEXT NOT NULL,
    final_price    INTEGER NOT NULL,
    payment_method TEXT NOT NULL CHECK (payment_method IN ('cash','finance','lease'))
);

CREATE TABLE inventory (
    id           INTEGER PRIMARY KEY,
    vehicle_id   INTEGER NOT NULL REFERENCES vehicles(id),
    branch_id    INTEGER NOT NULL REFERENCES branches(id),
    quantity     INTEGER NOT NULL CHECK (quantity >= 0),
    last_updated TEXT NOT NULL,
    UNIQUE (vehicle_id, branch_id)
);

CREATE INDEX idx_sales_sale_date  ON sales(sale_date);
CREATE INDEX idx_sales_branch_id  ON sales(branch_id);
CREATE INDEX idx_sales_vehicle_id ON sales(vehicle_id);
"""


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def gen_branches():
    return [(i, city, country, opened) for i, (city, country, opened) in enumerate(BRANCHES, 1)]


def gen_employees(branches):
    """50 employees: 1 Branch Manager, 1 Sales Manager, 1 Finance Advisor per
    branch (30), plus 20 Sales Reps spread 2 per branch."""
    salary_ranges = {
        "Branch Manager": (110000, 160000),
        "Sales Manager": (80000, 115000),
        "Finance Advisor": (60000, 85000),
        "Sales Rep": (40000, 65000),
    }
    rows, emp_id = [], 1
    for b_id, city, country, opened in branches:
        firsts, lasts = NAMES[country]
        opened_d = date.fromisoformat(opened)
        for role in ["Branch Manager", "Sales Manager", "Finance Advisor", "Sales Rep", "Sales Rep"]:
            hire = rand_date(opened_d, date(2023, 12, 31))
            lo, hi = salary_ranges[role]
            salary = round(random.randint(lo, hi), -2)
            rows.append((emp_id, random.choice(firsts), random.choice(lasts), role, b_id,
                         hire.isoformat(), salary))
            emp_id += 1
    return rows


def gen_customers(n=200):
    countries = list(CUSTOMER_LOCATIONS)
    weights = [3 if c not in FOREIGN_MARKET_BRANCH else 1 for c in countries]
    rows = []
    for i in range(1, n + 1):
        country = random.choices(countries, weights)[0]
        city = random.choice(CUSTOMER_LOCATIONS[country])
        firsts, lasts = NAMES[country]
        ctype = "business" if random.random() < 0.25 else "private"
        join = rand_date(date(2018, 1, 1), date(2024, 10, 31))
        rows.append((i, random.choice(firsts), random.choice(lasts), country, city, ctype,
                     join.isoformat()))
    return rows


def gen_vehicles():
    """One row per model x model-year (2018-2024). Price inflates ~4%/year."""
    rows, v_id = [], 1
    for brand, model, category, price_2024 in MODELS:
        first = MODEL_FIRST_YEAR.get(model, 2018)
        last = MODEL_LAST_YEAR.get(model, 2024)
        for year in range(first, last + 1):
            price = round(price_2024 / (1.04 ** (2024 - year)), -2)
            color = random.choices(COLORS, COLOR_WEIGHTS)[0]
            rows.append((v_id, brand, model, year, category, int(price), color))
            v_id += 1
    return rows


def gen_sales(n, vehicles, customers, employees, branches):
    branch_by_city = {city: b_id for b_id, city, _, _ in branches}
    branch_by_country = {country: b_id for b_id, _, country, _ in branches}

    # Customer -> branch they buy at (their own country's branch, or nearest hub).
    def home_branch(country):
        if country in branch_by_country:
            return branch_by_country[country]
        return branch_by_city[FOREIGN_MARKET_BRANCH[country]]

    customers_by_branch = {}
    for c in customers:
        customers_by_branch.setdefault(home_branch(c[3]), []).append(c)

    sellers_by_branch = {}
    for e in employees:
        if e[3] in ("Sales Rep", "Sales Manager"):
            sellers_by_branch.setdefault(e[4], []).append(e)

    # Pre-compute weighted (year, month) buckets for the seasonal trend.
    buckets, bucket_w = [], []
    for y in range(2020, 2025):
        for m in range(1, 13):
            buckets.append((y, m))
            bucket_w.append(YEAR_WEIGHTS[y] * MONTH_WEIGHTS[m])

    branch_ids = [b[0] for b in branches]
    branch_w = [BRANCH_SALES_WEIGHT[b[1]] for b in branches]

    rows = []
    while len(rows) < n:
        y, m = random.choices(buckets, bucket_w)[0]
        month_end = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
        sale_d = rand_date(date(y, m, 1), month_end)

        b_id = random.choices(branch_ids, branch_w)[0]

        # Customer must have joined on/before the sale date.
        cands = [c for c in customers_by_branch.get(b_id, []) if c[6] <= sale_d.isoformat()]
        if not cands:
            continue
        cust = random.choice(cands)

        # Seller must have been hired on/before the sale date.
        sellers = [e for e in sellers_by_branch[b_id] if e[5] <= sale_d.isoformat()]
        if not sellers:
            # Fall back to any staff at the branch hired by then (e.g. Branch Manager).
            sellers = [e for e in employees if e[4] == b_id and e[5] <= sale_d.isoformat()]
        if not sellers:
            continue
        emp = random.choice(sellers)

        # Vehicle model year: sale year, previous year, or next year (released
        # early in the fall), and within 2018-2024.
        allowed_years = {sale_d.year - 1, sale_d.year}
        if sale_d.month >= 9:
            allowed_years.add(sale_d.year + 1)
        veh_cands = [v for v in vehicles if v[3] in allowed_years]
        # Business customers lean toward trucks/SUVs/luxury fleet cars.
        if cust[5] == "business":
            vw = [3 if v[4] in ("Truck", "SUV", "Luxury") else 1 for v in veh_cands]
        else:
            vw = [3 if v[4] in ("Sedan", "SUV") else 2 if v[4] == "Electric" else 1 for v in veh_cands]
        # Electric cars gain popularity over time.
        vw = [w * (1 + 0.35 * (sale_d.year - 2020)) if v[4] == "Electric" else w
              for w, v in zip(vw, veh_cands)]
        veh = random.choices(veh_cands, vw)[0]

        # Final price within +-15% of base price (most deals near list).
        factor = max(0.85, min(1.15, random.gauss(1.0, 0.06)))
        final_price = int(round(veh[5] * factor, -1))

        if cust[5] == "business":
            payment = random.choices(["cash", "finance", "lease"], [20, 30, 50])[0]
        else:
            payment = random.choices(["cash", "finance", "lease"], [30, 50, 20])[0]

        rows.append((len(rows) + 1, veh[0], cust[0], emp[0], b_id, sale_d.isoformat(),
                     final_price, payment))

    rows.sort(key=lambda r: r[5])
    # Re-number ids chronologically.
    return [(i, *r[1:]) for i, r in enumerate(rows, 1)]


def gen_inventory(vehicles, branches):
    """Current stock: recent model years (2023-2024) at every branch."""
    rows, inv_id = [], 1
    for v in vehicles:
        if v[3] < 2023:
            continue
        for b in branches:
            qty = random.choices([0, 1, 2, 3, 4, 5, 6, 8, 10],
                                 [10, 15, 18, 16, 12, 10, 8, 6, 5])[0]
            if v[3] == 2023:
                qty = qty // 2  # older stock is being cleared out
            updated = rand_date(date(2024, 10, 1), date(2024, 12, 31))
            rows.append((inv_id, v[0], b[0], qty, updated.isoformat()))
            inv_id += 1
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)
    if os.path.exists(db_path):
        os.remove(db_path)

    branches = gen_branches()
    employees = gen_employees(branches)
    customers = gen_customers(200)
    vehicles = gen_vehicles()
    sales = gen_sales(1000, vehicles, customers, employees, branches)
    inventory = gen_inventory(vehicles, branches)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO branches VALUES (?,?,?,?)", branches)
        conn.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?,?)", employees)
        conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?)", customers)
        conn.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", vehicles)
        conn.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?,?)", sales)
        conn.executemany("INSERT INTO inventory VALUES (?,?,?,?,?)", inventory)
        conn.commit()

        print(f"Database created: {db_path}\n")
        print(f"{'Table':<12}{'Rows':>8}")
        print("-" * 20)
        for table in ["branches", "employees", "customers", "vehicles", "sales", "inventory"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table:<12}{count:>8}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
