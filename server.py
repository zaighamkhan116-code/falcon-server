from flask import Flask, request, render_template_string, jsonify, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ================= DATABASE ================= #

def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        account TEXT PRIMARY KEY,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS profits (
        account TEXT,
        balance REAL,
        equity REAL,
        profit REAL,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= SAVE DATA FROM MT5 ================= #

@app.route("/update", methods=["POST"])
def update():
    try:
        data = request.get_json()

        acc = str(data.get("account"))
        balance = float(data.get("balance", 0))
        equity = float(data.get("equity", 0))
        profit = equity - balance

        conn = sqlite3.connect("data.db")
        c = conn.cursor()

        c.execute("""
        INSERT INTO profits (account, balance, equity, profit, date)
        VALUES (?, ?, ?, ?, ?)
        """, (acc, balance, equity, profit, datetime.now().strftime("%Y-%m-%d")))

        conn.commit()
        conn.close()

        return "OK"
    except:
        return "ERROR"

# ================= LICENSE CHECK ================= #

@app.route("/check", methods=["POST"])
def check():
    acc = request.data.decode("utf-8").strip()

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT status FROM clients WHERE account=?", (acc,))
    row = c.fetchone()

    conn.close()

    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "blocked"})


# ================= DELETE ACCOUNT ================= #

@app.route("/delete/<acc>")
def delete(acc):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("DELETE FROM clients WHERE account=?", (acc,))
    c.execute("DELETE FROM profits WHERE account=?", (acc,))

    conn.commit()
    conn.close()

    return redirect("/")


# ================= PANEL ================= #

@app.route("/", methods=["GET", "POST"])
def panel():

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    # ADD / UPDATE ACCOUNT
    if request.method == "POST":
        acc = request.form.get("account")
        status = request.form.get("status")

        if acc:
            c.execute("""
            INSERT INTO clients(account, status)
            VALUES (?, ?)
            ON CONFLICT(account) DO UPDATE SET status=excluded.status
            """, (acc, status))

            conn.commit()

    # GET DATA
    c.execute("""
    SELECT c.account, c.status,
           IFNULL(MAX(p.balance),0),
           IFNULL(SUM(p.profit),0)
    FROM clients c
    LEFT JOIN profits p ON c.account = p.account
    GROUP BY c.account
    """)

    data = c.fetchall()

    conn.close()

    # TOTALS
    total_daily = sum([row[3] for row in data])
    total_weekly = total_daily
    total_monthly = total_daily
    total_overall = total_daily

    rows_html = ""
    i = 1

    for acc, status, balance, profit in data:

        status_color = "green" if status == "active" else "red"
        profit_color = "green" if profit >= 0 else "red"

        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{acc}</td>
            <td style='color:{status_color}; font-weight:bold;'>{status}</td>
            <td>-</td>
            <td>{round(balance,2)}</td>
            <td style='color:{profit_color}'>{round(profit,2)}</td>
            <td style='color:{profit_color}'>{round(profit,2)}</td>
            <td style='color:{profit_color}'>{round(profit,2)}</td>
            <td>0</td>
            <td style='color:{profit_color}'>{round(profit,2)}</td>
            <td><a href="/delete/{acc}" style="background:red;color:white;padding:5px 10px;text-decoration:none;">Delete</a></td>
        </tr>
        """

        i += 1

    return render_template_string(f"""

<html>
<head>
<title>Forex Falcon</title>

<style>
body {{
    font-family: Arial;
    background: #dcd6e0;
    text-align: center;
}}

h1 {{
    color: red;
}}

h2 {{
    color: purple;
    font-size: 40px;
}}

.container {{
    width: calc(100% - 2in);
    margin: auto;
}}

.box {{
    display: inline-block;
    background: #3aa0b3;
    padding: 20px;
    margin: 20px;
    border-radius: 10px;
}}

input, select {{
    padding: 5px;
    margin: 5px;
}}

button {{
    padding: 5px 10px;
}}

.summary {{
    display: flex;
    justify-content: center;
    gap: 20px;
}}

.summary div {{
    border: 1px solid black;
    padding: 10px 20px;
    background: #eee;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}}

td, th {{
    border: 1px solid black;
    padding: 8px;
}}

</style>
</head>

<body>

<h1>DASHBOARD</h1>
<h2>THE FOREX FALCON</h2>

<div class="container">

<div class="box">
<h3>Check Status</h3>
<form method="POST" action="/check">
<input name="account" placeholder="Account">
<br>
<button>ENTER</button>
</form>
</div>

<div class="box">
<h3>Add / Update Account</h3>
<form method="POST">
<input name="account" placeholder="Account" required>
<br>
<select name="status">
<option value="active">Active</option>
<option value="blocked">Blocked</option>
</select>
<br>
<button>Save</button>
</form>
</div>

<h3>{datetime.now().strftime("%d %b %Y")}</h3>

<div class="summary">
<div>Total Daily = {round(total_daily,2)}</div>
<div>Total Weekly = {round(total_weekly,2)}</div>
<div>Total Monthly = {round(total_monthly,2)}</div>
<div>Total Overall = {round(total_overall,2)}</div>
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
<th>Action</th>
</tr>

{rows_html}

</table>

</div>

</body>
</html>

""")

# ================= RUN ================= #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
