from flask import Flask, send_from_directory, jsonify, request
import sqlite3
import os

app = Flask(__name__)

DB = "expenses.db"


# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
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


# ---------------- PAGES ----------------

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/analytics.html")
def analytics():
    return send_from_directory(".", "analytics.html")


# ---------------- EXPENSES ----------------

@app.route("/api/expenses", methods=["GET"])
def get_expenses():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC, id DESC"
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

    try:

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO expenses
            (amount, category, note, date)
            VALUES (?, ?, ?, ?)
            """,
            (
                float(amount),
                category,
                note,
                date
            )
        )

        conn.commit()

        expense_id = cursor.lastrowid

        conn.close()

        return jsonify({
            "success": True,
            "id": expense_id
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# ---------------- AI ASSISTANT ----------------

@app.route("/api/ai", methods=["POST"])
def ai_assistant():

    data = request.get_json() or {}

    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "answer": "Please enter a question."
        }), 400


    # Get expenses
    conn = get_db()

    rows = conn.execute(
        """
        SELECT amount, category, note, date
        FROM expenses
        ORDER BY date DESC
        """
    ).fetchall()

    conn.close()


    expenses = [dict(row) for row in rows]


    # Basic calculations
    total = sum(
        float(expense["amount"])
        for expense in expenses
    )

    transaction_count = len(expenses)


    categories = {}

    for expense in expenses:

        category = expense["category"]

        categories[category] = (
            categories.get(category, 0)
            + float(expense["amount"])
        )


    if categories:

        top_category = max(
            categories,
            key=categories.get
        )

    else:

        top_category = "None"


    # API key
    api_key = os.getenv("OPENAI_API_KEY")


    if not api_key:

        return jsonify({
            "answer":
            "⚠️ OPENAI_API_KEY is not configured in Render."
        })


    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key
        )


        expense_summary = "\n".join(
            [
                f"- {e['date']} | "
                f"{e['category']} | "
                f"₹{float(e['amount']):,.2f} | "
                f"{e['note'] or 'No description'}"
                for e in expenses
            ]
        )


        prompt = f"""
You are an intelligent personal finance assistant.

Answer the user's question using ONLY the expense information
provided below.

User question:
{question}

Total spending:
₹{total:,.2f}

Number of transactions:
{transaction_count}

Category totals:
{categories}

Highest spending category:
{top_category}

Expense records:
{expense_summary}

Give a clear and useful answer.

Use Indian Rupees (₹).

If the user asks for advice, provide practical and
reasonable suggestions.

Never invent expenses or financial information.
"""


        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )


        answer = response.output_text


        return jsonify({
            "answer": answer
        })


    except Exception as e:

        print("AI ERROR:", repr(e))

        return jsonify({
            "answer":
            "⚠️ AI request failed.\n\n"
            "Error: " + str(e)
        })


# ---------------- HEALTH ----------------

@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "message": "Smart Expense Tracker is running"
    })


# ---------------- START ----------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
