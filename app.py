from flask import Flask, send_from_directory, jsonify, request
import sqlite3
import os

app = Flask(__name__)
DB = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/analytics.html")
def analytics():
    return send_from_directory(".", "analytics.html")

@app.route("/api/expenses")
def expenses():
    conn = get_db()
    data = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC,id DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(x) for x in data])

@app.route("/api/expenses", methods=["POST"])
def add():
    d = request.get_json()

    if not d.get("amount") or not d.get("category") or not d.get("date"):
        return jsonify({"success":False,"error":"Fill required fields"}),400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO expenses(amount,category,note,date) VALUES(?,?,?,?)",
        (d["amount"],d["category"],d.get("note",""),d["date"])
    )
    conn.commit()
    conn.close()

    return jsonify({"success":True,"id":cur.lastrowid})

@app.route("/api/expenses/<int:eid>", methods=["DELETE"])
def delete(eid):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
    conn.commit()
    conn.close()
    return jsonify({"success":True})

@app.route("/api/ai", methods=["POST"])
def ai():

    data = request.get_json() or {}
    question = data.get("question","").strip()

    conn = get_db()
    rows = conn.execute(
        "SELECT amount,category,note,date FROM expenses"
    ).fetchall()
    conn.close()

    expenses = [dict(x) for x in rows]

    total = sum(float(x["amount"]) for x in expenses)
    count = len(expenses)

    categories = {}

    for x in expenses:
        c = x["category"]
        categories[c] = categories.get(c,0) + float(x["amount"])

    top = max(categories,key=categories.get) if categories else "None"

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return jsonify({
            "answer":
            f"📊 You have {count} transactions totaling ₹{total:,.2f}. "
            f"Your highest spending category is {top}. "
            f"Add an OPENAI_API_KEY in Render Environment Variables "
            f"to enable full AI answers."
        })

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        prompt = f"""
You are a helpful personal expense assistant.

User question:
{question}

Expense data:
Total spent: ₹{total:.2f}
Transactions: {count}
Category totals: {categories}

Give a short, practical answer.
Use Indian Rupees.
Do not invent transactions.
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return jsonify({
            "answer": response.output_text
        })

    except Exception as e:
        return jsonify({
            "answer":
            f"📊 Total spending: ₹{total:,.2f}. "
            f"Transactions: {count}. "
            f"Top category: {top}. "
            f"AI service is temporarily unavailable."
        })

@app.route("/api/health")
def health():
    return jsonify({
        "success":True,
        "message":"Smart Expense Tracker is running"
    })

if __name__ == "__main__":
    app.run()
