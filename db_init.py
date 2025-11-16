# db_init.py
# Initialize SQLite DB for CSP Use Case.
# Run standalone: python db_init.py
# Or it will be called from server.py if csp.db is missing.

import sqlite3
import os
import datetime
import random

DB = "csp.db"


def seed():
    if os.path.exists(DB):
        os.remove(DB)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # ---------------- Tables ----------------
    cur.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msisdn TEXT UNIQUE,
            name TEXT,
            age INTEGER,
            gender TEXT,
            region TEXT,
            city TEXT,
            occupation TEXT,
            marital_status TEXT,
            income_bracket TEXT,
            device_brand TEXT,
            device_type TEXT,
            hobby TEXT,
            preferred_app TEXT,
            data_preference TEXT,
            voice_preference TEXT,
            churn_risk_score REAL
        );

        CREATE TABLE customer_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            income_bracket TEXT,
            email TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE usage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            date TEXT,
            data_mb REAL,
            call_minutes REAL,
            sms_count INTEGER,
            app_usage_score REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT
        );

        CREATE TABLE customer_segment_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            segment_id INTEGER,
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            assigned_by TEXT,
            method TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (segment_id) REFERENCES segments(id)
        );

        CREATE TABLE offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            title TEXT,
            description TEXT,
            eligibility_simple TEXT,
            active INTEGER
        );

        CREATE TABLE offer_assignment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            offer_id INTEGER,
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            assigned_by TEXT,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (offer_id) REFERENCES offers(id)
        );
        """
    )

    # ---------------- Sample customers ----------------
    customers = [
        ("9990000001", "Alice", 29, "F", "South", "Chennai", "Software Engineer", "Single", "high", "Apple", "iPhone 14", "Streaming", "YouTube", "High", "Medium", 0.10),
        ("9990000002", "Bob", 35, "M", "South", "Bengaluru", "Manager", "Married", "medium", "Samsung", "Galaxy S22", "Gaming", "PUBG", "High", "Low", 0.25),
        ("9990000003", "Charlie", 42, "M", "South", "Hyderabad", "Teacher", "Married", "low", "Xiaomi", "Mi 11", "Browsing", "Chrome", "Medium", "Medium", 0.18),
        ("9990000004", "Dave", 31, "M", "West", "Mumbai", "Designer", "Single", "high", "Apple", "iPhone 13", "Streaming", "Netflix", "High", "Low", 0.08),
        ("9990000005", "Eve", 27, "F", "North", "Delhi", "Student", "Single", "low", "Samsung", "A52", "Social Media", "Instagram", "Medium", "High", 0.35),
    ]
    cur.executemany(
        """
        INSERT INTO customers (msisdn,name,age,gender,region,city,occupation,marital_status,
                               income_bracket,device_brand,device_type,hobby,preferred_app,
                               data_preference,voice_preference,churn_risk_score)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        customers,
    )

    # Profiles
    cur.execute("SELECT id, income_bracket, name FROM customers")
    for cid, income, name in cur.fetchall():
        email = f"{name.lower()}@example.com"
        cur.execute(
            "INSERT INTO customer_profile (customer_id, income_bracket, email) VALUES (?,?,?)",
            (cid, income, email),
        )

    # ---------------- Sample usage_history ----------------
    cur.execute("SELECT id FROM customers")
    cust_ids = [r[0] for r in cur.fetchall()]
    today = datetime.date.today()
    rng = random.Random(42)
    usage_rows = []
    for cid in cust_ids:
        for d in range(30):
            day = today - datetime.timedelta(days=d)
            data_mb = rng.randint(100, 5000)
            call_minutes = rng.randint(10, 200)
            sms_count = rng.randint(0, 50)
            app_usage_score = rng.randint(1, 10)
            usage_rows.append(
                (cid, day.isoformat(), float(data_mb), float(call_minutes), sms_count, float(app_usage_score))
            )
    cur.executemany(
        """
        INSERT INTO usage_history (customer_id,date,data_mb,call_minutes,sms_count,app_usage_score)
        VALUES (?,?,?,?,?,?)
        """,
        usage_rows,
    )

    # ---------------- Sample offers ----------------
    offers = [
        ("OFR001", "Starter Pack", "2GB for 7 days", "", 1),
        ("OFR002", "High Value Data", "50GB monthly for heavy users", "income_bracket=high", 1),
        ("OFR003", "Streaming Add-on", "Extra 10GB for video apps", "preferred_app=YouTube", 1),
        ("OFR004", "Gaming Boost", "5GB gaming data", "preferred_app=PUBG", 1),
        ("OFR005", "Social Media Pack", "Unlimited Instagram + Facebook", "preferred_app=Instagram", 1),
        ("OFR006", "Work From Home Pack", "15GB daytime data", "", 1),
        ("OFR007", "Voice Unlimited", "Unlimited calling for 28 days", "", 1),
        ("OFR008", "Weekend Binge", "20GB weekend only", "min_avg_data_mb=200", 1),
        ("OFR009", "South Region Offer", "Special pack for South region", "region=South", 1),
        ("OFR010", "Apple Device Offer", "Offer for Apple users", "device_brand=Apple", 1),
    ]
    cur.executemany(
        "INSERT INTO offers (code,title,description,eligibility_simple,active) VALUES (?,?,?,?,?)",
        offers,
    )

    conn.commit()
    conn.close()
    print("Database seeded:", DB)


if __name__ == "__main__":
    seed()
