from flask import Flask, send_from_directory, jsonify, request
import sqlite3, os, json, re

app = Flask(__name__)
DB = "expenses.db"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()

    c.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        note TEXT,
        date TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS income(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        source TEXT NOT NULL,
        date TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS recurring(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        frequency TEXT NOT NULL,
        next_date TEXT NOT NULL
    )
    """)

    c.commit()
    c.close()


init_db()


# ---------------- PAGES ----------------

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


@app.route("/coach.html")
def coach():
    return send_from_directory(".", "coach.html")


@app.route("/intelligence.html")
def intelligence():
    return send_from_directory(".", "intelligence.html")


@app.route("/budget.html")
def budget():
    return send_from_directory(".", "budget.html")


# ---------------- EXPENSES ----------------

@app.route("/api/expenses")
def expenses():
    c = db()

    r = c.execute(
        "SELECT * FROM expenses ORDER BY date DESC,id DESC"
    ).fetchall()

    c.close()

    return jsonify([dict(x) for x in r])


@app.route("/api/expenses", methods=["POST"])
def add_expense():

    d = request.get_json() or {}

    if not d.get("amount") or not d.get("category") or not d.get("date"):
        return jsonify(
            success=False,
            error="Please fill all required fields."
        ), 400

    c = db()

    x = c.execute(
        """
        INSERT INTO expenses
        (amount,category,note,date)
        VALUES(?,?,?,?)
        """,
        (
            float(d["amount"]),
            d["category"],
            d.get("note", ""),
            d["date"]
        )
    )

    c.commit()

    i = x.lastrowid

    c.close()

    return jsonify(
        success=True,
        id=i
    )


@app.route("/api/expenses/<int:i>", methods=["DELETE"])
def delete_expense(i):

    c = db()

    c.execute(
        "DELETE FROM expenses WHERE id=?",
        (i,)
    )

    c.commit()
    c.close()

    return jsonify(success=True)


# ---------------- INCOME ----------------

@app.route("/api/income")
def income():

    c = db()

    r = c.execute(
        "SELECT * FROM income ORDER BY date DESC,id DESC"
    ).fetchall()

    c.close()

    return jsonify([dict(x) for x in r])


@app.route("/api/income", methods=["POST"])
def add_income():

    d = request.get_json() or {}

    if not d.get("amount") or not d.get("source") or not d.get("date"):
        return jsonify(
            success=False,
            error="Please fill all income fields."
        ), 400

    c = db()

    x = c.execute(
        """
        INSERT INTO income
        (amount,source,date)
        VALUES(?,?,?)
        """,
        (
            float(d["amount"]),
            d["source"],
            d["date"]
        )
    )

    c.commit()

    i = x.lastrowid

    c.close()

    return jsonify(
        success=True,
        id=i
    )


@app.route("/api/income/<int:i>", methods=["DELETE"])
def delete_income(i):

    c = db()

    c.execute(
        "DELETE FROM income WHERE id=?",
        (i,)
    )

    c.commit()
    c.close()

    return jsonify(success=True)


# ---------------- FINANCIAL SUMMARY ----------------

@app.route("/api/financial-summary")
def financial_summary():

    c = db()

    income_total = c.execute(
        "SELECT COALESCE(SUM(amount),0) FROM income"
    ).fetchone()[0]

    expense_total = c.execute(
        "SELECT COALESCE(SUM(amount),0) FROM expenses"
    ).fetchone()[0]

    c.close()

    income_total = float(income_total)
    expense_total = float(expense_total)

    return jsonify(
        total_income=income_total,
        total_expenses=expense_total,
        balance=income_total - expense_total
    )


# ---------------- RECURRING ----------------

@app.route("/api/recurring")
def get_recurring():

    c = db()

    r = c.execute(
        "SELECT * FROM recurring ORDER BY next_date"
    ).fetchall()

    c.close()

    return jsonify([dict(x) for x in r])


@app.route("/api/recurring", methods=["POST"])
def add_recurring():

    d = request.get_json() or {}

    if not d.get("name") or not d.get("amount") or not d.get("next_date"):
        return jsonify(
            success=False,
            error="Please fill all recurring payment fields."
        ), 400

    c = db()

    x = c.execute(
        """
        INSERT INTO recurring
        (name,amount,frequency,next_date)
        VALUES(?,?,?,?)
        """,
        (
            d["name"],
            float(d["amount"]),
            d.get("frequency", "monthly"),
            d["next_date"]
        )
    )

    c.commit()

    i = x.lastrowid

    c.close()

    return jsonify(
        success=True,
        id=i
    )


@app.route("/api/recurring/<int:i>", methods=["DELETE"])
def delete_recurring(i):

    c = db()

    c.execute(
        "DELETE FROM recurring WHERE id=?",
        (i,)
    )

    c.commit()
    c.close()

    return jsonify(success=True)


# ---------------- FINANCIAL DATA FOR AI ----------------

def financial_data():

    c = db()

    expenses = [
        dict(x)
        for x in c.execute(
            """
            SELECT amount,category,note,date
            FROM expenses
            """
        ).fetchall()
    ]

    income = [
        dict(x)
        for x in c.execute(
            """
            SELECT amount,source,date
            FROM income
            """
        ).fetchall()
    ]

    recurring = [
        dict(x)
        for x in c.execute(
            """
            SELECT name,amount,frequency,next_date
            FROM recurring
            """
        ).fetchall()
    ]

    c.close()

    return expenses, income, recurring


# ---------------- AI MONEY COACH ----------------

@app.route("/api/ai", methods=["POST"])
def ai():

    d = request.get_json() or {}

    # Supports both old and new AI Coach versions
    question = (
        d.get("question")
        or d.get("message")
        or ""
    ).strip()

    if not question:

        return jsonify(
            success=False,
            answer="Please enter a question."
        ), 400

    expenses, income, recurring = financial_data()

    total_expenses = sum(
        float(x["amount"])
        for x in expenses
    )

    total_income = sum(
        float(x["amount"])
        for x in income
    )

    balance = total_income - total_expenses

    monthly_recurring = 0

    for x in recurring:

        amount = float(x["amount"])

        if x["frequency"] == "weekly":
            monthly_recurring += amount * 52 / 12

        elif x["frequency"] == "yearly":
            monthly_recurring += amount / 12

        else:
            monthly_recurring += amount

    key = os.getenv("OPENAI_API_KEY")

    if not key:

        return jsonify(
            success=True,
            answer=(
                f"Income: ₹{total_income:,.2f}\n"
                f"Expenses: ₹{total_expenses:,.2f}\n"
                f"Balance: ₹{balance:,.2f}\n"
                f"Recurring: ₹{monthly_recurring:,.2f}/month"
            )
        )

    try:

        from openai import OpenAI

        client = OpenAI(api_key=key)

        prompt = f"""
You are the AI Financial Coach inside a personal
expense tracking application.

Answer the user's question using the financial
information provided below.

USER QUESTION:
{question}

TOTAL INCOME:
₹{total_income:,.2f}

TOTAL EXPENSES:
₹{total_expenses:,.2f}

CURRENT BALANCE:
₹{balance:,.2f}

MONTHLY RECURRING PAYMENTS:
₹{monthly_recurring:,.2f}

EXPENSE RECORDS:
{expenses}

INCOME RECORDS:
{income}

RECURRING PAYMENTS:
{recurring}

Rules:

- Use Indian Rupees.
- Be practical and concise.
- Explain calculations when useful.
- Never invent financial information.
- Identify useful savings opportunities.
- Give actionable advice.
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return jsonify(
            success=True,
            answer=response.output_text
        )

    except Exception as ex:

        print(
            "AI ERROR:",
            repr(ex)
        )

        return jsonify(
            success=False,
            answer=(
                "⚠️ AI service error. "
                "Please try again later."
            )
        ), 500


# ---------------- AI RECEIPT SCANNER ----------------

@app.route("/api/scan-receipt", methods=["POST"])
def scan_receipt():

    d = request.get_json() or {}

    image = d.get("image", "")

    if not image:

        return jsonify(
            success=False,
            error="Please upload a receipt image."
        ), 400

    key = os.getenv("OPENAI_API_KEY")

    if not key:

        return jsonify(
            success=False,
            error="AI service is not configured."
        ), 500

    try:

        from openai import OpenAI

        client = OpenAI(api_key=key)

        if not image.startswith("data:image/"):

            image = (
                "data:image/jpeg;base64,"
                + image
            )

        prompt = """
Read this receipt carefully.

Find the FINAL TOTAL AMOUNT PAID.

Do NOT use:
- item prices
- subtotal
- tax alone
- discount
- change
- quantity

Use the final grand total or amount paid.

Return ONLY valid JSON:

{
  "amount": 123.45,
  "category": "Food",
  "note": "Merchant name",
  "date": "YYYY-MM-DD"
}

Category must be one of:

Food
Travel
Shopping
Bills
Education
Entertainment
Health
Other

If the receipt date is visible,
convert it to YYYY-MM-DD.

Never invent an amount.
"""

        response = client.responses.create(

            model="gpt-5.6-luna",

            input=[
                {
                    "role": "user",

                    "content": [

                        {
                            "type": "input_text",
                            "text": prompt
                        },

                        {
                            "type": "input_image",
                            "image_url": image
                        }

                    ]
                }
            ]
        )

        text = (
            response.output_text or ""
        ).strip()

        print(
            "RECEIPT AI RESULT:",
            text
        )

        text = (
            text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if not match:

            raise ValueError(
                "AI returned invalid receipt data."
            )

        result = json.loads(
            match.group(0)
        )

        amount = result.get(
            "amount",
            0
        )

        if isinstance(amount, str):

            cleaned = re.sub(
                r"[^0-9.]",
                "",
                amount
            )

            amount = (
                float(cleaned)
                if cleaned
                else 0
            )

        allowed = {
            "Food",
            "Travel",
            "Shopping",
            "Bills",
            "Education",
            "Entertainment",
            "Health",
            "Other"
        }

        category = str(
            result.get(
                "category",
                "Other"
            )
        )

        if category not in allowed:

            category = "Other"

        note = str(
            result.get(
                "note",
                "Receipt"
            )
        ).strip()

        if not note:

            note = "Receipt"

        date = str(
            result.get(
                "date",
                ""
            )
        ).strip()

        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            date
        ):

            date = ""

        print(
            "RECEIPT FINAL:",
            amount,
            category,
            note,
            date
        )

        return jsonify(

            success=True,

            amount=amount,

            category=category,

            note=note,

            date=date

        )

    except Exception as ex:

        print(
            "RECEIPT ERROR:",
            repr(ex)
        )

        return jsonify(
            success=False,
            error=(
                "Could not read the receipt. "
                "Please take a clearer photo."
            )
        ), 500


# ---------------- HEALTH ----------------

@app.route("/api/health")
def health():

    return jsonify(
        success=True,
        message="Smart Expense Tracker is running"
    )


# ---------------- START SERVER ----------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
        )
