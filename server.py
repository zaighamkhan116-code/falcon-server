from flask import Flask, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ================= DATABASE ================= #
def init_db():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        account TEXT PRIMARY KEY,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS profits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,
        balance REAL,
        equity REAL,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= LICENSE ================= #
@app.route("/check", methods=["POST"])
def check():
    data = request.data.decode().strip()

    try:
        acc, server, key = data.split("|")
    except:
        return "blocked"

    acc = str(int(acc))  # FIX ACCOUNT FORMAT

    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT status FROM clients WHERE account=?", (acc,))
    row = c.fetchone()

    conn.close()

    if row and row[0].strip().lower() == "active":
        return "active"

    return "blocked"

# ================= DATA RECEIVE ================= #
@app.route("/update", methods=["POST"])
def update():
    import json

    try:
        data = json.loads(request.data.decode())
    except:
        return "error"

    acc = str(int(data.get("account")))
    balance = float(data.get("balance", 0))
    equity = float(data.get("equity", 0))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO profits (account, balance, equity, timestamp)
    VALUES (?, ?, ?, ?)
    """, (acc, balance, equity, now))

    conn.commit()
    conn.close()

    return "ok"

# ================= STATUS CHECK ================= #
@app.route("/status", methods=["POST"])
def status():
    acc = request.form.get("acc")
    acc = str(acc)

    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT status FROM clients WHERE account=?", (acc,))
    row = c.fetchone()

    conn.close()

    if row:
        return f"Status: {row[0]}"
    return "Account not found"

# ================= ADD ACCOUNT ================= #
@app.route("/add", methods=["POST"])
def add():
    acc = request.form.get("acc")
    acc = str(int(acc))
    status = request.form.get("status")

    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO clients (account, status)
    VALUES (?, ?)
    """, (acc, status))

    conn.commit()
    conn.close()

    return redirect("/")

# ================= DELETE ================= #
@app.route("/delete/<acc>")
def delete(acc):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("DELETE FROM clients WHERE account=?", (acc,))
    c.execute("DELETE FROM profits WHERE account=?", (acc,))

    conn.commit()
    conn.close()

    return redirect("/")

# ================= DASHBOARD ================= #
@app.route("/")
def dashboard():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT account, status FROM clients")
    clients = c.fetchall()

    rows = ""
    total_daily = 0

    i = 1

    for acc, status in clients:

        c.execute("SELECT balance FROM profits WHERE account=? ORDER BY id DESC LIMIT 1", (acc,))
        last = c.fetchone()
        balance = last[0] if last else 0

        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("""
        SELECT balance FROM profits 
        WHERE account=? AND timestamp LIKE ?
        ORDER BY id ASC LIMIT 1
        """, (acc, today + "%"))
        first = c.fetchone()

        daily = 0
        if first:
            daily = balance - first[0]

        total_daily += daily

        rows += f"""
        <tr>
        <td>{i}</td>
        <td>{acc}</td>
        <td>{status}</td>
        <td>-</td>
        <td>{round(balance,2)}</td>
        <td>{round(daily,2)}</td>
        <td>{round(daily,2)}</td>
        <td>{round(daily,2)}</td>
        <td>0</td>
        <td>{round(daily,2)}</td>
        <td><a class="del" href="/delete/{acc}">Delete</a></td>
        </tr>
        """
        i += 1

    conn.close()

    html = f"""
    <html>
    <head>
    <style>
    body {{background:#dcd3e6;font-family:Arial;text-align:center;}}

    h1 {{color:red;}}
    h2 {{color:#7b2cbf;font-size:40px;font-weight:bold;}}

    .container {{width:95%;margin:auto;}}

    .card {{
        background:#2a9db3;
        padding:20px;
        margin:20px;
        display:inline-block;
        border-radius:10px;
        width:320px;
        color:white;
    }}

    input,select {{padding:6px;margin:5px;}}

    .box {{
        display:inline-block;
        margin:10px;
        padding:10px;
        border:1px solid black;
        width:200px;
        background:white;
    }}

    table {{
        width:90%;
        margin:20px auto;
        border-collapse:collapse;
    }}

    td,th {{
        border:1px solid black;
        padding:8px;
    }}

    .del {{
        background:red;
        color:white;
        padding:5px 10px;
        text-decoration:none;
    }}
    </style>
    </head>

    <body>
    <div class="container">

    <h1>DASHBOARD</h1>
    <h2>THE FOREX FALCON</h2>

    <div class="card">
    <h3>Check Status</h3>
    <form method="POST" action="/status">
    <input name="acc" placeholder="Account"><br>
    <button type="submit">ENTER</button>
    </form>
    </div>

    <div class="card">
    <h3>Add / Update Account</h3>
    <form method="POST" action="/add">
    <input name="acc" placeholder="Account"><br>
    <select name="status">
    <option value="active">Active</option>
    <option value="blocked">Blocked</option>
    </select><br>
    <button type="submit">Save</button>
    </form>
    </div>

    <h3>{datetime.now().strftime("%d %B %Y")}</h3>

    <div class="box">Total Daily = {round(total_daily,2)}</div>
    <div class="box">Total Weekly = {round(total_daily,2)}</div>
    <div class="box">Total Monthly = {round(total_daily,2)}</div>
    <div class="box">Total Overall = {round(total_daily,2)}</div>

    <table>
    <tr>
    <th>Ser</th><th>Acc ID</th><th>Status</th><th>Hrs</th>
    <th>Balance($)</th><th>Daily</th><th>Weekly</th>
    <th>Monthly</th><th>Last Month</th><th>Overall</th><th>Action</th>
    </tr>

    {rows}

    </table>

    </div>
    </body>
    </html>
    """

    return html

# ================= RUN ================= #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
