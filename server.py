from flask import Flask, request, render_template_string, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ================= DATABASE ================= #
def init_db():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    # UNIQUE account (no duplicates)
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

# ================= LICENSE CHECK ================= #
@app.route("/check", methods=["POST"])
def check():
    data = request.data.decode().strip()

    try:
        acc, server, key = data.split("|")
    except:
        return "blocked"

    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT status FROM clients WHERE account=?", (acc,))
    row = c.fetchone()

    conn.close()

    if row and row[0] == "active":
        return "active"
    else:
        return "blocked"

# ================= DATA RECEIVE ================= #
@app.route("/update", methods=["POST"])
def update():
    raw = request.data.decode("utf-8")

    import json
    try:
        data = json.loads(raw)
    except:
        return "error"

    acc = data.get("account")
    balance = data.get("balance")
    equity = data.get("equity")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    # INSERT DATA
    c.execute("""
    INSERT INTO profits (account, balance, equity, timestamp)
    VALUES (?, ?, ?, ?)
    """, (acc, balance, equity, now))

    conn.commit()
    conn.close()

    return "ok"

# ================= DELETE ACCOUNT ================= #
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

    rows_html = ""
    total_daily = 0

    i = 1

    for acc, status in clients:

        # LAST BALANCE
        c.execute("""
        SELECT balance FROM profits 
        WHERE account=? ORDER BY id DESC LIMIT 1
        """, (acc,))
        last = c.fetchone()
        balance = last[0] if last else 0

        # FIRST TODAY
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("""
        SELECT balance FROM profits 
        WHERE account=? AND timestamp LIKE ?
        ORDER BY id ASC LIMIT 1
        """, (acc, today + "%"))
        first_today = c.fetchone()

        daily = 0
        if first_today:
            daily = balance - first_today[0]

        total_daily += daily

        rows_html += f"""
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
            <td><a href="/delete/{acc}" style="color:red;">Delete</a></td>
        </tr>
        """

        i += 1

    conn.close()

    html = f"""
    <html>
    <body style="font-family:Arial; text-align:center;">

    <h1>DASHBOARD</h1>
    <h2>THE FOREX FALCON</h2>

    <form method="POST" action="/add">
        Account: <input name="acc">
        Status:
        <select name="status">
            <option value="active">Active</option>
            <option value="blocked">Blocked</option>
        </select>
        <button type="submit">Save</button>
    </form>

    <h3>Total Daily = {round(total_daily,2)}</h3>

    <table border="1" style="margin:auto;">
    <tr>
    <th>Ser</th><th>Acc ID</th><th>Status</th><th>Hrs</th>
    <th>Balance</th><th>Daily</th><th>Weekly</th>
    <th>Monthly</th><th>Last Month</th><th>Overall</th><th>Action</th>
    </tr>

    {rows_html}

    </table>

    </body>
    </html>
    """

    return html

# ================= ADD ACCOUNT ================= #
@app.route("/add", methods=["POST"])
def add():
    acc = request.form.get("acc")
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

# ================= RUN ================= #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
