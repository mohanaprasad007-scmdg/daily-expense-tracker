from flask import Flask, send_from_directory, jsonify, request
import sqlite3

app = Flask(__name__)

DB = "expenses.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    conn = get_db()

    expenses = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC, id DESC"
    ).fetchall()

    conn.close()

    return jsonify([
        dict(expense) for expense in expenses
    ])


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.get_json()

    amount = data.get("amount")
    category = data.get("category")
    note = data.get("note", "")
    date = data.get("date")

    if not amount or not category or not date:
        return jsonify({
            "success": False,
            "error": "Missing required information"
        }), 400

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO expenses
        (amount, category, note, date)
        VALUES (?, ?, ?, ?)
        """,
        (amount, category, note, date)
    )

    conn.commit()

    expense_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "id": expense_id
    })


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


@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "Smart Expense Tracker is running"
    })


if __name__ == "__main__":
    app.run(debug=True)
