from flask import Flask, send_from_directory, jsonify, request
import sqlite3
import os

app = Flask(__name__)
DB = "expenses.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT,
            date TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            source TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/analytics.html")
def analytics():
    return send_from_directory(".", "analytics.html")


@app.route("/goals.html")
def goals():
    return send_from_directory(".", "goals.html")


# ---------------- EXPENSES ----------------

@app.route("/api/expenses", methods=["GET"])
def get_expenses():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC,id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/expenses", methods=["POST"])
def add_expense():

    data = request.get_json() or {}

    amount = data.get("amount")
    category = data.get("category")
    note = data.get("note", "")
    date = data.get("date")

    if not amount or not category or not date:
        return jsonify({
            "success": False,
            "error": "Please fill all required fields."
        }), 400

    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO expenses(amount,category,note,date)
        VALUES(?,?,?,?)
        """,
        (float(amount), category, note, date)
    )

    conn.commit()
    expense_id = cur.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "id": expense_id
    })


@app.route("/api/expenses/<int:eid>", methods=["DELETE"])
def delete_expense(eid):

    conn = get_db()

    conn.execute(
        "DELETE FROM expenses WHERE id=?",
        (eid,)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})


# ---------------- INCOME ----------------

@app.route("/api/income", methods=["GET"])
def get_income():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM income ORDER BY date DESC,id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/income", methods=["POST"])
def add_income():

    data = request.get_json() or {}

    amount = data.get("amount")
    source = data.get("source")
    date = data.get("date")

    if not amount or not source or not date:
        return jsonify({
            "success": False,
            "error": "Please fill all income fields."
        }), 400

    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO income(amount,source,date)
        VALUES(?,?,?)
        """,
        (float(amount), source, date)
    )

    conn.commit()
    income_id = cur.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "id": income_id
    })


@app.route("/api/income/<int:iid>", methods=["DELETE"])
def delete_income(iid):

    conn = get_db()

    conn.execute(
        "DELETE FROM income WHERE id=?",
        (iid,)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})


# ---------------- FINANCIAL SUMMARY ----------------

@app.route("/api/financial-summary")
def financial_summary():

    conn = get_db()

    expense = conn.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM expenses"
    ).fetchone()["total"]

    income = conn.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM income"
    ).fetchone()["total"]

    conn.close()

    return jsonify({
        "income": float(income),
        "expenses": float(expense),
        "balance": float(income) - float(expense)
    })


# ---------------- AI ----------------

@app.route("/api/ai", methods=["POST"])
def ai_assistant():

    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "answer": "Please enter a question."
        }), 400

    conn = get_db()

    expenses = [
        dict(x) for x in conn.execute(
            "SELECT amount,category,note,date FROM expenses"
        ).fetchall()
    ]

    income = [
        dict(x) for x in conn.execute(
            "SELECT amount,source,date FROM income"
        ).fetchall()
    ]

    conn.close()

    total_expenses = sum(
        float(x["amount"]) for x in expenses
    )

    total_income = sum(
        float(x["amount"]) for x in income
    )

    balance = total_income - total_expenses

    categories = {}

    for x in expenses:

        category = x["category"]

        categories[category] = (
            categories.get(category, 0)
            + float(x["amount"])
        )

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return jsonify({
            "answer": (
                f"Income: ₹{total_income:,.2f}\n"
                f"Expenses: ₹{total_expenses:,.2f}\n"
                f"Balance: ₹{balance:,.2f}"
            )
        })

    try:

        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        prompt = f"""
You are a personal finance assistant.

User question:
{question}

Financial information:

Total income:
₹{total_income:,.2f}

Total expenses:
₹{total_expenses:,.2f}

Current balance:
₹{balance:,.2f}

Category spending:
{categories}

Expense records:
{expenses}

Income records:
{income}

Give a concise, practical answer.
Use Indian Rupees.
Do not invent financial information.
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return jsonify({
            "answer": response.output_text
        })

    except Exception as e:

        print("AI ERROR:", repr(e))

        return jsonify({
            "answer": (
                f"Income: ₹{total_income:,.2f}\n"
                f"Expenses: ₹{total_expenses:,.2f}\n"
                f"Balance: ₹{balance:,.2f}\n\n"
                "AI service is temporarily unavailable."
            )
        })


# ---------------- HEALTH ----------------

@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "message": "Smart Expense Tracker is running"
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
