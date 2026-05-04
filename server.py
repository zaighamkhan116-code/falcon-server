from flask import Flask, request, jsonify
import sqlite3, json
from datetime import datetime

app = Flask(__name__)

DB = "data.db"
licenses = {}
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

    # Parse incoming data (JSON / form / args)
    try:
        data = json.loads(raw)
    except:
        data = request.form.to_dict()

    if not data:
        data = request.args.to_dict()

    # 🔥 FIX: parse raw string from EA
    parts = raw.split("|")

    acc = parts[0] if len(parts) > 0 else ""

    # 🔥 READ FROM DATABASE (NOT memory)
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT status FROM licenses WHERE account=?", (acc,))
    row = c.fetchone()

    conn.close()

    status = row[0] if row else "blocked"

    return jsonify({"status": status})

# ================= UPDATE =================
@app.route("/update", methods=["POST"])
def update():
    raw = request.data.decode("utf-8").strip().replace("\x00","")
    print("RAW DATA:", raw)
    
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
    INSERT OR REPLACE INTO clients(account,balance,equity,last_equity,updated)
    VALUES(?,?,?,?,?)
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
    key = request.form.get("key")

    if key != SECRET_KEY:
        return "Unauthorized", 403

    acc = request.form.get("account")
    status = request.form.get("status")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT OR REPLACE INTO licenses(account,status) VALUES(?,?)", (acc, status))

    conn.commit()
    conn.close()
    return "<a href='/'>Back</a>"

# ================= DASHBOARD =================
@app.route("/")
def dashboard():

    today_str = datetime.utcnow().strftime("%d %b %Y").upper()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT l.account, IFNULL(c.balance, 0)
    FROM licenses l
    LEFT JOIN clients c ON l.account = c.account
    """)
    data = c.fetchall()

    rows_html = ""
    total_daily = total_weekly = total_monthly = total_overall = 0

    i = 1

    for acc, balance in data:

        c.execute("SELECT status FROM licenses WHERE account=?", (acc,))
        row = c.fetchone()
        status = row[0] if row else "blocked"

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND date LIKE ?", (acc, today()+"%"))
        daily = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND strftime('%Y-%W', date)=?", (acc, week()))
        weekly = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND strftime('%Y-%m', date)=?", (acc, month()))
        monthly = c.fetchone()[0] or 0

        c.execute("SELECT SUM(profit) FROM profits WHERE account=? AND strftime('%Y-%m', date)=?", (acc, last_month()))
        lastm = c.fetchone()[0] or 0

        # ✅ FIXED overall
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

    .date {{ font-size:24px; margin:20px; }}

    .stats {{ display:flex; justify-content:center; gap:40px; margin:20px; }}

    .statbox {{ border:1px solid black; padding:12px; width:260px; background:white; }}

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
            <h3>Check Status</h3>
            Account:<br><input><br><br>
            <button>ENTER</button>
        </div>

        <div class="box">
            <h3>Add / Update Account</h3>
            <form action="/set" method="post">
            <input type="hidden" name="key" value="MCdgsp4@">

            Account:<br>
            <input name="account" value="262793453" required><br>

            Status:<br>
            <select name="status">
              <option value="active" {"selected" if status=="active" else ""}>Active</option>
              <option value="blocked" {"selected" if status=="blocked" else ""}>Blocked</option>
            </select>

            <button type="submit">Save</button>
            </form>
            
        </div>
    </div>

    <div class="date">{today_str}</div>

    <div class="stats">
        <div class="statbox">Total Daily = ${round(total_daily,2)}</div>
        <div class="statbox">Total Weekly = ${round(total_weekly,2)}</div>
        <div class="statbox">Total Monthly = ${round(total_monthly,2)}</div>
        <div class="statbox">Total Overall = ${round(total_overall,2)}</div>
    </div>

    <table>
    <tr>
        <th>Ser</th>
        <th>Acc ID</th>
        <th>Status</th>
        <th>Hrs</th>
        <th>Balance($)</th>
        <th>Daily</th>
        <th>Weekly</th>
        <th>Monthly</th>
        <th>Last Month</th>
        <th>Overall</th>
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
