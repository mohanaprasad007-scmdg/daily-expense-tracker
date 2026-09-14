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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recurring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            frequency TEXT NOT NULL,
            next_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------- PAGES ----------

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/analytics.html")
def analytics():
    return send_from_directory(".", "analytics.html")


@app.route("/goals.html")
def goals():
    return send_from_directory(".", "goals.html")


@app.route("/recurring.html")
def recurring():
    return send_from_directory(".", "recurring.html")


# ---------- EXPENSES ----------

@app.route("/api/expenses", methods=["GET"])
def get_expenses():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC,id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(x) for x in rows])


@app.route("/api/expenses", methods=["POST"])
def add_expense():

    data = request.get_json() or {}

    if not data.get("amount") or not data.get("category") or not data.get("date"):
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
        (
            float(data["amount"]),
            data["category"],
            data.get("note", ""),
            data["date"]
        )
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


# ---------- INCOME ----------

@app.route("/api/income", methods=["GET"])
def get_income():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM income ORDER BY date DESC,id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(x) for x in rows])


@app.route("/api/income", methods=["POST"])
def add_income():

    data = request.get_json() or {}

    if not data.get("amount") or not data.get("source") or not data.get("date"):
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
        (
            float(data["amount"]),
            data["source"],
            data["date"]
        )
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


# ---------- FINANCIAL SUMMARY ----------

@app.route("/api/financial-summary")
def financial_summary():

    conn = get_db()

    income = conn.execute(
        "SELECT COALESCE(SUM(amount),0) total FROM income"
    ).fetchone()["total"]

    expenses = conn.execute(
        "SELECT COALESCE(SUM(amount),0) total FROM expenses"
    ).fetchone()["total"]

    recurring = conn.execute(
        "SELECT COALESCE(SUM(amount),0) total FROM recurring"
    ).fetchone()["total"]

    conn.close()

    return jsonify({
        "income": float(income),
        "expenses": float(expenses),
        "balance": float(income) - float(expenses),
        "recurring": float(recurring)
    })


# ---------- RECURRING PAYMENTS ----------

@app.route("/api/recurring", methods=["GET"])
def get_recurring():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM recurring ORDER BY next_date"
    ).fetchall()

    conn.close()

    return jsonify([dict(x) for x in rows])


@app.route("/api/recurring", methods=["POST"])
def add_recurring():

    data = request.get_json() or {}

    if not data.get("name") or not data.get("amount") or not data.get("next_date"):
        return jsonify({
            "success": False,
            "error": "Please fill all recurring payment fields."
        }), 400

    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO recurring
        (name,amount,frequency,next_date)
        VALUES(?,?,?,?)
        """,
        (
            data["name"],
            float(data["amount"]),
            data.get("frequency", "monthly"),
            data["next_date"]
        )
    )

    conn.commit()

    recurring_id = cur.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "id": recurring_id
    })


@app.route("/api/recurring/<int:rid>", methods=["DELETE"])
def delete_recurring(rid):

    conn = get_db()

    conn.execute(
        "DELETE FROM recurring WHERE id=?",
        (rid,)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})


# ---------- AI ASSISTANT ----------

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
            """
            SELECT amount,category,note,date
            FROM expenses
            ORDER BY date DESC
            """
        ).fetchall()
    ]

    income = [
        dict(x) for x in conn.execute(
            """
            SELECT amount,source,date
            FROM income
            ORDER BY date DESC
            """
        ).fetchall()
    ]

    recurring = [
        dict(x) for x in conn.execute(
            """
            SELECT name,amount,frequency,next_date
            FROM recurring
            ORDER BY next_date
            """
        ).fetchall()
    ]

    conn.close()


    total_expenses = sum(
        float(x["amount"])
        for x in expenses
    )

    total_income = sum(
        float(x["amount"])
        for x in income
    )

    balance = total_income - total_expenses


    recurring_monthly = 0

    for payment in recurring:

        amount = float(payment["amount"])

        if payment["frequency"] == "weekly":
            recurring_monthly += amount * 52 / 12

        elif payment["frequency"] == "yearly":
            recurring_monthly += amount / 12

        else:
            recurring_monthly += amount


    categories = {}

    for expense in expenses:

        category = expense["category"]

        categories[category] = (
            categories.get(category, 0)
            + float(expense["amount"])
        )


    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:

        return jsonify({
            "answer": (
                f"Income: ₹{total_income:,.2f}\n"
                f"Expenses: ₹{total_expenses:,.2f}\n"
                f"Balance: ₹{balance:,.2f}\n"
                f"Recurring commitments: ₹{recurring_monthly:,.2f}/month"
            )
        })


    try:

        from openai import OpenAI

        client = OpenAI(api_key=api_key)


        prompt = f"""
You are the AI financial assistant inside a personal
expense tracking application.

Answer the user's question using the financial data below.

USER QUESTION:
{question}

TOTAL INCOME:
₹{total_income:,.2f}

TOTAL EXPENSES:
₹{total_expenses:,.2f}

CURRENT BALANCE:
₹{balance:,.2f}

ESTIMATED MONTHLY RECURRING COMMITMENTS:
₹{recurring_monthly:,.2f}

CATEGORY SPENDING:
{categories}

EXPENSES:
{expenses}

INCOME:
{income}

RECURRING PAYMENTS:
{recurring}

Rules:

1. Use only the provided information.
2. Never invent transactions.
3. Use Indian Rupees.
4. Give practical and easy-to-understand answers.
5. Consider recurring commitments when discussing affordability.
6. If information is insufficient, clearly say so.
7. Keep the response reasonably short.
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
            "answer":
            "⚠️ AI service error. Please try again later."
        })


# ---------- HEALTH ----------

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
