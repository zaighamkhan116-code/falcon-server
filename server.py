from flask import Flask, request, jsonify, redirect
import sqlite3, json
from datetime import datetime

app = Flask(__name__)

DB = "data.db"
SECRET_KEY = "MCdgsp4@"   

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients(
        account TEXT PRIMARY KEY,
        balance REAL,
        equity REAL,
        last_equity REAL,
        updated TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS licenses(
        account TEXT PRIMARY KEY,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS profits(
        account TEXT,
        date TEXT,
        profit REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= HELPERS =================
def today():
    return datetime.utcnow().strftime("%Y-%m-%d")

def week():
    return datetime.utcnow().strftime("%Y-%W")

def month():
    return datetime.utcnow().strftime("%Y-%m")

def last_month():
    now = datetime.utcnow()
    m = now.month - 1 or 12
    y = now.year if now.month != 1 else now.year - 1
    return f"{y}-{str(m).zfill(2)}"

# ================= LICENSE =================
@app.route("/check", methods=["POST"])
def check():
    raw = request.data.decode("utf-8").strip().replace("\x00","")

    acc = ""

    # JSON
    try:
        data = json.loads(raw)
        acc = str(data.get("account", ""))
    except:
        pass

    # fallback old format
    if not acc and "|" in raw:
        acc = raw.split("|")[0]

    # fallback form
    if not acc:
        data = request.form.to_dict()
        if not data:
            data = request.args.to_dict()
        acc = str(data.get("account", ""))

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT status FROM licenses WHERE account=?", (acc,))
    row = c.fetchone()
    conn.close()

    return jsonify({"status": row[0] if row else "blocked"})

# ================= UPDATE =================
@app.route("/update", methods=["POST"])
def update():
    raw = request.data.decode("utf-8").strip().replace("\x00","")

    try:
        data = json.loads(raw)
    except:
        data = request.form.to_dict()

    if not data:
        data = request.args.to_dict()

    acc = str(data.get("account", "0"))
    balance = float(data.get("balance", 0))
    equity = float(data.get("equity", 0))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT last_equity FROM clients WHERE account=?", (acc,))
    row = c.fetchone()

    last_eq = row[0] if row else equity
    profit_change = equity - last_eq

    c.execute("""
    INSERT INTO clients(account,balance,equity,last_equity,updated)
    VALUES(?,?,?,?,?)
    ON CONFLICT(account) DO UPDATE SET
        balance=excluded.balance,
        equity=excluded.equity,
        last_equity=excluded.equity,
        updated=excluded.updated
    """, (acc, balance, equity, equity, datetime.utcnow()))

    c.execute("""
    INSERT INTO profits(account,date,profit)
    VALUES(?,?,?)
    """, (acc, datetime.utcnow().isoformat(), profit_change))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# ================= ADD ACCOUNT =================
@app.route("/set", methods=["POST"])
def set_account():
    if request.form.get("key") != SECRET_KEY:
        return "Unauthorized", 403

    acc = request.form.get("account")
    status = request.form.get("status")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO licenses(account,status) VALUES(?,?)", (acc, status))
    conn.commit()
    conn.close()

    return redirect("/")

# ================= DELETE =================
@app.route("/delete", methods=["POST"])
def delete():
    acc = request.form.get("account")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE account=?", (acc,))
    c.execute("DELETE FROM licenses WHERE account=?", (acc,))
    c.execute("DELETE FROM profits WHERE account=?", (acc,))
    conn.commit()
    conn.close()

    return redirect("/")

# ================= DASHBOARD =================
@app.route("/")
def dashboard():

    today_str = datetime.utcnow().strftime("%d %b %Y").upper()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT l.account, IFNULL(MAX(c.balance),0)
    FROM licenses l
    LEFT JOIN clients c ON l.account = c.account
    GROUP BY l.account
    """)
    data = c.fetchall()

    rows_html = ""
    total_daily = total_weekly = total_monthly = total_overall = 0

    i = 1

    for acc, balance in data:

        c.execute("SELECT status FROM licenses WHERE account=?", (acc,))
        status = c.fetchone()[0]

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND date LIKE ?", (acc, today()+"%"))
        daily = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND strftime('%Y-%W', date)=?", (acc, week()))
        weekly = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND strftime('%Y-%m', date)=?", (acc, month()))
        monthly = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND strftime('%Y-%m', date)=?", (acc, last_month()))
        lastm = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=?", (acc,))
        overall = c.fetchone()[0] or 0

        total_daily += daily
        total_weekly += weekly
        total_monthly += monthly
        total_overall += overall

        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{acc}</td>
            <td>{status}</td>
            <td>-</td>
            <td>{round(balance,2)}</td>
            <td>{round(daily,2)}</td>
            <td>{round(weekly,2)}</td>
            <td>{round(monthly,2)}</td>
            <td>{round(lastm,2)}</td>
            <td>{round(overall,2)}</td>
            <td>
                <form method="POST" action="/delete">
                    <input type="hidden" name="account" value="{acc}">
                    <button style="background:red;color:white;">Delete</button>
                </form>
            </td>
        </tr>
        """

        i += 1

    conn.close()

    html = f"""
    <html>
    <head>
    <style>
    body {{ background:#eee6f7; font-family:Arial; text-align:center; }}
    .title1 {{ color:red; font-size:24px; }}
    .title2 {{ color:#7a3db8; font-size:46px; font-weight:bold; }}
    .container {{ display:flex; justify-content:center; gap:120px; margin:30px; }}
    .box {{ background:#2aa4cf; padding:25px; border-radius:10px; width:320px; color:white; }}
    table {{ margin:auto; border-collapse:collapse; width:95%; background:white; }}
    th, td {{ border:1px solid black; padding:10px; }}
    th {{ background:#ddd; }}
    </style>
    </head>

    <body>

    <div class="title1">DASHBOARD</div>
    <div class="title2">THE FOREX FALCON</div>

    <div class="container">
        <div class="box">
            <form action="/set" method="post">
                <input type="hidden" name="key" value="{SECRET_KEY}">
                Account:<br><input name="account"><br><br>
                <select name="status">
                    <option value="active">Active</option>
                    <option value="blocked">Blocked</option>
                </select><br><br>
                <button type="submit">Save</button>
            </form>
        </div>
    </div>

    <table>
    <tr>
        <th>Ser</th>
        <th>Acc ID</th>
        <th>Status</th>
        <th>Hrs</th>
        <th>Balance</th>
        <th>Daily</th>
        <th>Weekly</th>
        <th>Monthly</th>
        <th>Last Month</th>
        <th>Overall</th>
        <th>Action</th>
    </tr>
    {rows_html}
    </table>

    </body>
    </html>
    """

    return html

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
