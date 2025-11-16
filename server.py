# server.py 
# Minimal dependency-free HTTP server for CSP Use Case
# Place this file in your project root (same folder as csp.db, db_init.py and frontend/)
# Run: python server.py

import os
import sqlite3
import json
import io
import csv
import datetime
import time
import math
import uuid
from wsgiref.simple_server import make_server
from urllib.parse import parse_qs

# Import local simple KMeans implementation
from simple_kmeans import kmeans

DB = "csp.db"
FRONTEND_DIR = "frontend"
OUTBOX_DIR = "outbox"

os.makedirs(OUTBOX_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def respond_json(start_response, status, obj):
    payload = json.dumps(obj, default=str).encode("utf-8")
    headers = [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))]
    start_response(status, headers)
    return [payload]


def serve_static(environ, start_response, path):
    # basic static file serving for frontend
    rel = path.lstrip("/")
    if rel == "" or rel == "/":
        rel = "index.html"
    full = os.path.join(FRONTEND_DIR, rel)
    if not os.path.exists(full) or not os.path.isfile(full):
        start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
        return [b"Not Found"]
    # basic content type detection
    if full.endswith(".html"):
        ctype = "text/html"
    elif full.endswith(".js"):
        ctype = "application/javascript"
    elif full.endswith(".css"):
        ctype = "text/css"
    elif full.endswith(".csv"):
        ctype = "text/csv"
    elif full.endswith(".json"):
        ctype = "application/json"
    else:
        ctype = "application/octet-stream"
    with open(full, "rb") as f:
        data = f.read()
    start_response("200 OK", [("Content-Type", ctype), ("Content-Length", str(len(data)))])
    return [data]


def parse_post(environ):
    # parse JSON body or form-encoded body
    try:
        size = int(environ.get("CONTENT_LENGTH", 0) or 0)
    except:
        size = 0
    body = environ["wsgi.input"].read(size) if size > 0 else b""
    if not body:
        return {}
    ct = environ.get("CONTENT_TYPE", "")
    if "application/json" in ct:
        try:
            return json.loads(body.decode("utf-8"))
        except:
            return {}
    # fallback parse form
    try:
        return {k: v[0] for k, v in parse_qs(body.decode("utf-8")).items()}
    except:
        return {}


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Serve frontend static files when requested
    if path.startswith("/static/") or path == "/" or path.endswith(".html") or path.endswith(".js") or path.endswith(".css"):
        return serve_static(environ, start_response, path if path != "/" else "/")

    # ---------------------------------------------------------------------
    # CUSTOMERS
    # ---------------------------------------------------------------------

    # API: GET customers
    if path == "/api/customers" and method == "GET":
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, msisdn, name, age, gender, region, city, occupation, marital_status,
                   income_bracket, device_brand, device_type, hobby, preferred_app,
                   data_preference, voice_preference, churn_risk_score
            FROM customers
            ORDER BY id
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return respond_json(start_response, "200 OK", rows)

    # API: CSV upload (POST) - expects JSON { "csv": "<csv text>" }
    if path == "/api/customers/upload" and method == "POST":
        body = parse_post(environ)
        csv_text = body.get("csv") or ""
        if not csv_text:
            return respond_json(start_response, "400 Bad Request", {"error": "CSV text required"})

        try:
            f = io.StringIO(csv_text)
            reader = csv.DictReader(f)
        except Exception as e:
            return respond_json(start_response, "400 Bad Request", {"error": "Invalid CSV", "details": str(e)})

        inserted = 0
        errors = []
        conn = get_db()
        cur = conn.cursor()
        for idx, row in enumerate(reader, start=2):  # start=2 to account for header
            try:
                msisdn = row.get("msisdn") or row.get("MSISDN")
                if not msisdn:
                    errors.append({"row": idx, "error": "Missing msisdn"})
                    continue

                vals = [
                    msisdn,
                    row.get("name"),
                    int(row["age"]) if row.get("age") else None,
                    row.get("gender"),
                    row.get("region"),
                    row.get("city"),
                    row.get("occupation"),
                    row.get("marital_status"),
                    row.get("income_bracket"),
                    row.get("device_brand"),
                    row.get("device_type"),
                    row.get("hobby"),
                    row.get("preferred_app"),
                    row.get("data_preference"),
                    row.get("voice_preference"),
                    float(row["churn_risk_score"]) if row.get("churn_risk_score") else None,
                ]

                cur.execute(
                    """
                    INSERT INTO customers
                      (msisdn,name,age,gender,region,city,occupation,marital_status,
                       income_bracket,device_brand,device_type,hobby,preferred_app,
                       data_preference,voice_preference,churn_risk_score)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    vals,
                )
                inserted += 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        conn.commit()
        conn.close()
        return respond_json(start_response, "200 OK", {"inserted": inserted, "errors": errors})

    # API: export customers.csv
    if path == "/api/export/customers.csv" and method == "GET":
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT msisdn, name, age, gender, region, city, occupation, marital_status, income_bracket, device_brand, device_type, hobby, preferred_app, data_preference, voice_preference, churn_risk_score FROM customers"
        )
        rows = cur.fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "msisdn",
                "name",
                "age",
                "gender",
                "region",
                "city",
                "occupation",
                "marital_status",
                "income_bracket",
                "device_brand",
                "device_type",
                "hobby",
                "preferred_app",
                "data_preference",
                "voice_preference",
                "churn_risk_score",
            ]
        )
        for r in rows:
            writer.writerow([r[k] for k in r.keys()])
        data = output.getvalue().encode("utf-8")
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/csv"),
                ("Content-Disposition", "attachment; filename=customers.csv"),
                ("Content-Length", str(len(data))),
            ],
        )
        return [data]

    # ---------------------------------------------------------------------
    # OFFERS
    # ---------------------------------------------------------------------

    # API: GET offers
    if path == "/api/offers" and method == "GET":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, code, title, description, eligibility_simple, active FROM offers")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return respond_json(start_response, "200 OK", rows)

    # API: UPLOAD offers CSV
    if path == "/api/offers/upload" and method == "POST":
        body = parse_post(environ)
        csv_text = body.get("csv") or ""
        if not csv_text:
            return respond_json(start_response, "400 Bad Request", {"error": "CSV text required"})

        try:
            reader = csv.DictReader(io.StringIO(csv_text))
        except Exception as e:
            return respond_json(start_response, "400 Bad Request", {"error": "Invalid CSV", "details": str(e)})

        inserted = 0
        errors = []
        conn = get_db()
        cur = conn.cursor()

        for idx, row in enumerate(reader, start=2):
            try:
                code = (row.get("code") or "").strip()
                title = (row.get("title") or "").strip()
                if not code or not title:
                    errors.append({"row": idx, "error": "Missing code or title"})
                    continue

                desc = row.get("description")
                elig = row.get("eligibility_simple")
                act_raw = (row.get("active") or "1").strip().lower()
                if act_raw in ("1", "true", "yes"):
                    active = 1
                else:
                    active = 0

                cur.execute(
                    """
                    INSERT INTO offers
                        (code, title, description, eligibility_simple, active)
                    VALUES (?,?,?,?,?)
                """,
                    (code, title, desc, elig, active),
                )

                inserted += 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        conn.commit()
        conn.close()
        return respond_json(start_response, "200 OK", {"inserted": inserted, "errors": errors})

    # API: GET offer assignments
    if path == "/api/offer_assignments" and method == "GET":
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id, c.msisdn as customer_msisdn, o.code as offer_code, a.assigned_at, a.assigned_by, a.status
            FROM offer_assignment a
            LEFT JOIN customers c ON c.id = a.customer_id
            LEFT JOIN offers o ON o.id = a.offer_id
            ORDER BY a.assigned_at DESC
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return respond_json(start_response, "200 OK", rows)

    # API: assign offer to customer (simple) - writes note to outbox and inserts assignment
    if path == "/api/offers/assign" and method == "POST":
        body = parse_post(environ)
        try:
            customer_id = int(body.get("customer_id") or 0)
            offer_id = int(body.get("offer_id") or 0)
        except:
            return respond_json(start_response, "400 Bad Request", {"error": "customer_id and offer_id required"})

        notify_email = (body.get("notify_email") or "").strip()

        conn = get_db()
        cur = conn.cursor()
        # verify existence
        cur.execute("SELECT id, name, msisdn FROM customers WHERE id=?", (customer_id,))
        cust = cur.fetchone()
        if not cust:
            conn.close()
            return respond_json(start_response, "400 Bad Request", {"error": "customer_not_found"})

        cur.execute("SELECT id, code, title, description FROM offers WHERE id=?", (offer_id,))
        offer = cur.fetchone()
        if not offer:
            conn.close()
            return respond_json(start_response, "400 Bad Request", {"error": "offer_not_found"})

        try:
            # record assignment
            cur.execute(
                "INSERT INTO offer_assignment (customer_id, offer_id, assigned_by, status) VALUES (?,?,?,?)",
                (customer_id, offer_id, "admin_ui", "assigned"),
            )
            conn.commit()
            assignment_id = cur.lastrowid

            # write simple notification file for preview (no SMTP)
            note = (
                f"Assigned offer {offer['code']} ({offer['title']}) "
                f"to customer {cust.get('name') or cust.get('msisdn')} (id={customer_id})\n"
            )
            if notify_email:
                note += f"Notify email: {notify_email}\n"
            note += f"Description: {offer.get('description') or ''}\n"
            note += f"Assigned at: {datetime.datetime.utcnow().isoformat()}Z\n"

            fname = f"assign_{int(time.time())}_{uuid.uuid4().hex[:6]}.txt"
            path_out = os.path.join(OUTBOX_DIR, fname)
            with open(path_out, "w", encoding="utf-8") as f:
                f.write(note)

            conn.close()
            return respond_json(
                start_response,
                "200 OK",
                {"status": "assigned", "assignment_id": assignment_id, "note": path_out},
            )
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            return respond_json(start_response, "500 Internal Server Error", {"error": str(e)})

    # ---------------------------------------------------------------------
    # SEGMENTS / SEGMENTATION
    # ---------------------------------------------------------------------

    # API: segments list
    if path == "/api/segments_list" and method == "GET":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, description FROM segments")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return respond_json(start_response, "200 OK", rows)

    # SEGMENTATION: demographic-based KMeans
    if path == "/api/segment/run" and method == "POST":
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, msisdn, name, age, gender, region, city, income_bracket, device_brand,
                       device_type, hobby, preferred_app, data_preference, voice_preference, churn_risk_score
                FROM customers
            """
            )
            customers = [dict(r) for r in cur.fetchall()]
            if not customers:
                conn.close()
                return respond_json(start_response, "200 OK", {"status": "no_customers"})

            # mapping helpers
            def map_income(v):
                if not v:
                    return 1.0
                m = {"low": 0.0, "medium": 1.0, "high": 2.0}
                return m.get(str(v).lower(), 1.0)

            def map_pref(v):
                if not v:
                    return 1.0
                vv = str(v).strip().lower()
                if vv == "high":
                    return 2.0
                if vv == "medium":
                    return 1.0
                if vv == "low":
                    return 0.0
                return 1.0

            def map_gender(v):
                if not v:
                    return 0.5
                v = str(v).strip().upper()
                return 1.0 if v == "F" else 0.0

            def norm_hash(s):
                if not s:
                    return 0.0
                return (abs(hash(str(s))) % 1000) / 1000.0

            raw_points = []
            id_list = []
            meta = []
            for c in customers:
                id_list.append(c["id"])
                age = float(c["age"]) if c.get("age") is not None else 30.0
                income = float(map_income(c.get("income_bracket")))
                churn = float(c.get("churn_risk_score") or 0.0)
                data_pref = float(map_pref(c.get("data_preference")))
                voice_pref = float(map_pref(c.get("voice_preference")))
                gender = float(map_gender(c.get("gender")))
                region_hash = float(norm_hash(c.get("region")))
                device_hash = float(norm_hash(c.get("device_brand")))
                # feature vector (order): age, income, churn, data_pref, voice_pref, gender, region_hash, device_hash
                vec = [age, income, churn, data_pref, voice_pref, gender, region_hash, device_hash]
                raw_points.append(vec)
                meta.append({"id": c["id"], "msisdn": c.get("msisdn"), "name": c.get("name")})

            # normalize features (min-max per column)
            cols = len(raw_points[0])
            mins = [math.inf] * cols
            maxs = [-math.inf] * cols
            for v in raw_points:
                for i in range(cols):
                    mins[i] = min(mins[i], v[i])
                    maxs[i] = max(maxs[i], v[i])
            ranges = [(maxs[i] - mins[i]) if (maxs[i] - mins[i]) > 0 else 1.0 for i in range(cols)]
            points = []
            for v in raw_points:
                norm = [(v[i] - mins[i]) / ranges[i] for i in range(cols)]
                points.append(norm)

            # choose K proportional to sqrt(N) heuristic (but at least 2, at most 10)
            n = max(1, len(points))
            K = max(2, int(round(math.sqrt(n))))
            if K > 10:
                K = 10
            seed = int(time.time() // 60)

            # run KMeans
            labels, centroids = kmeans(points, k=K, max_iter=100, seed=seed)

            # create or find segment rows for labels
            seg_map = {}
            for lab in sorted(set(labels)):
                name = f"Attr-Segment-{lab}"
                cur.execute("SELECT id FROM segments WHERE name=?", (name,))
                row = cur.fetchone()
                if row:
                    seg_id = row["id"]
                else:
                    cur.execute(
                        "INSERT INTO segments (name, description) VALUES (?,?)",
                        (name, "Generated from demographics"),
                    )
                    seg_id = cur.lastrowid
                seg_map[lab] = seg_id

            # clear previous mappings (demo behavior)
            cur.execute("DELETE FROM customer_segment_map")
            conn.commit()

            # insert new mappings
            for cid, lab in zip(id_list, labels):
                cur.execute(
                    "INSERT INTO customer_segment_map (customer_id, segment_id, assigned_by, method) VALUES (?,?,?,?)",
                    (cid, seg_map[lab], "attr_kmeans", "demographics"),
                )
            conn.commit()

            # prepare response summary
            counts = {}
            samples = {}
            for lab, m in zip(labels, meta):
                lab_s = str(lab)
                counts[lab_s] = counts.get(lab_s, 0) + 1
                if lab_s not in samples:
                    samples[lab_s] = []
                if len(samples[lab_s]) < 5:
                    samples[lab_s].append(
                        {"id": m["id"], "msisdn": m.get("msisdn"), "name": m.get("name")}
                    )

            conn.close()
            return respond_json(
                start_response,
                "200 OK",
                {"status": "ok", "k": K, "assigned": len(labels), "clusters": counts, "samples": samples},
            )

        except Exception as e:
            try:
                conn.close()
            except:
                pass
            return respond_json(start_response, "500 Internal Server Error", {"error": str(e)})

    # ---------------------------------------------------------------------
    # OFFER GENERATION (RULE-BASED)
    # ---------------------------------------------------------------------

    # API: generate personalized offers for a customer
    if path == "/api/offers/generate" and method == "POST":
        body = parse_post(environ)
        try:
            customer_id = int(body.get("customer_id") or 0)
        except:
            return respond_json(start_response, "400 Bad Request", {"error": "customer_id required"})
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
        cust = cur.fetchone()
        if not cust:
            conn.close()
            return respond_json(start_response, "400 Bad Request", {"error": "customer_not_found"})
        # profile income (from customer_profile if exists)
        profile_income = None
        try:
            cur.execute("SELECT income_bracket FROM customer_profile WHERE customer_id=?", (customer_id,))
            prof = cur.fetchone()
            profile_income = prof["income_bracket"] if prof else None
        except:
            profile_income = cust["income_bracket"]

        # usage aggregates (if table exists and data present)
        try:
            cur.execute(
                """
                SELECT
                  AVG(data_mb)     as avg_data_mb,
                  AVG(call_minutes) as avg_call_mins,
                  AVG(sms_count)   as avg_sms,
                  AVG(app_usage_score) as avg_app_usage
                FROM usage_history WHERE customer_id=?
                """,
                (customer_id,),
            )
            agg = cur.fetchone()
            agg = {k: (agg[k] or 0) for k in agg.keys()} if agg else {}
        except:
            agg = {}
        if not agg:
            agg = {"avg_data_mb": 0, "avg_call_mins": 0, "avg_sms": 0, "avg_app_usage": 0}

        cur.execute("SELECT id, code, title, description, eligibility_simple FROM offers WHERE active=1")
        offers = cur.fetchall()
        matches = []
        for o in offers:
            elig = o["eligibility_simple"] or ""
            ok = False
            if elig.strip() == "":
                ok = True
            else:
                # very simple key=value parser
                conds = [p.strip() for p in elig.split(",") if p.strip()]
                ok = True
                for cond in conds:
                    if "=" in cond:
                        k2, v2 = cond.split("=", 1)
                        k2 = k2.strip()
                        v2 = v2.strip()
                        if k2 == "income_bracket":
                            if (profile_income or cust["income_bracket"]) != v2:
                                ok = False
                                break
                        elif k2 == "preferred_app":
                            if (cust["preferred_app"] or "").strip() != v2:
                                ok = False
                                break
                        elif k2 == "region":
                            if (cust["region"] or "").strip() != v2:
                                ok = False
                                break
                        elif k2 == "city":
                            if (cust["city"] or "").strip() != v2:
                                ok = False
                                break
                        elif k2 == "device_brand":
                            if (cust["device_brand"] or "").strip() != v2:
                                ok = False
                                break
                        elif k2 == "min_avg_data_mb":
                            try:
                                if float(agg.get("avg_data_mb", 0)) < float(v2):
                                    ok = False
                                    break
                            except:
                                ok = False
                                break
                        else:
                            # unknown key -> ignore
                            pass
                    else:
                        # unsupported expression -> ignore
                        pass
            if ok:
                score = 0.0
                if "min_avg_data_mb" in (o["eligibility_simple"] or ""):
                    score += float(agg.get("avg_data_mb", 0)) / 1000.0
                if (profile_income or cust["income_bracket"]) == "high" and "income_bracket=high" in (o["eligibility_simple"] or ""):
                    score += 10.0
                matches.append(
                    {
                        "offer_id": o["id"],
                        "code": o["code"],
                        "title": o["title"],
                        "score": round(score, 2),
                    }
                )
        matches = sorted(matches, key=lambda x: -x["score"])
        chosen = matches[0] if matches else None
        if chosen:
            cur.execute(
                "INSERT INTO offer_assignment (customer_id, offer_id, assigned_by, status) VALUES (?,?,?,?)",
                (customer_id, chosen["offer_id"], "system", "assigned"),
            )
            conn.commit()
            chosen["assignment_id"] = cur.lastrowid
        conn.close()
        return respond_json(
            start_response,
            "200 OK",
            {"customer_id": customer_id, "chosen_offer": chosen, "all_matches": matches, "aggregates": agg},
        )

    # fallback serve static file
    return serve_static(environ, start_response, path)


if __name__ == "__main__":
    # ensure DB exists (calls db_init.seed if missing)
    if not os.path.exists(DB):
        print("DB not found, running db_init.py to create it.")
        try:
            import db_init
            db_init.seed()
        except Exception as e:
            print("Failed to run db_init.py:", e)

    port = 5000
    print(f"Starting server on http://127.0.0.1:{port}")
    httpd = make_server("127.0.0.1", port, app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
