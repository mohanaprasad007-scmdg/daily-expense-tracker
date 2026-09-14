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
    c.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        note TEXT,
        date TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS income(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        source TEXT NOT NULL,
        date TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS recurring(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        frequency TEXT NOT NULL,
        next_date TEXT NOT NULL
    )""")
    c.commit()
    c.close()

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

@app.route("/recurring.html")
def recurring():
    return send_from_directory(".", "recurring.html")

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
        """INSERT INTO expenses
        (amount,category,note,date)
        VALUES(?,?,?,?)""",
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

    return jsonify(success=True, id=i)

@app.route("/api/expenses/<int:i>", methods=["DELETE"])
def delete_expense(i):
    c = db()
    c.execute("DELETE FROM expenses WHERE id=?", (i,))
    c.commit()
    c.close()
    return jsonify(success=True)

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
        """INSERT INTO income
        (amount,source,date)
        VALUES(?,?,?)""",
        (
            float(d["amount"]),
            d["source"],
            d["date"]
        )
    )

    c.commit()
    i = x.lastrowid
    c.close()

    return jsonify(success=True, id=i)

@app.route("/api/income/<int:i>", methods=["DELETE"])
def delete_income(i):
    c = db()
    c.execute("DELETE FROM income WHERE id=?", (i,))
    c.commit()
    c.close()
    return jsonify(success=True)

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
        """INSERT INTO recurring
        (name,amount,frequency,next_date)
        VALUES(?,?,?,?)""",
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

    return jsonify(success=True, id=i)

@app.route("/api/recurring/<int:i>", methods=["DELETE"])
def delete_recurring(i):
    c = db()
    c.execute("DELETE FROM recurring WHERE id=?", (i,))
    c.commit()
    c.close()
    return jsonify(success=True)

# ---------------- AI MONEY COACH ----------------

def financial_data():
    c = db()

    e = [
        dict(x)
        for x in c.execute(
            "SELECT amount,category,note,date FROM expenses"
        ).fetchall()
    ]

    inc = [
        dict(x)
        for x in c.execute(
            "SELECT amount,source,date FROM income"
        ).fetchall()
    ]

    rec = [
        dict(x)
        for x in c.execute(
            "SELECT name,amount,frequency,next_date FROM recurring"
        ).fetchall()
    ]

    c.close()

    return e, inc, rec

@app.route("/api/ai", methods=["POST"])
def ai():

    d = request.get_json() or {}
    q = d.get("question", "").strip()

    if not q:
        return jsonify(answer="Please enter a question."), 400

    e, inc, rec = financial_data()

    te = sum(float(x["amount"]) for x in e)
    ti = sum(float(x["amount"]) for x in inc)

    bal = ti - te

    rm = 0

    for x in rec:
        a = float(x["amount"])

        if x["frequency"] == "weekly":
            rm += a * 52 / 12
        elif x["frequency"] == "yearly":
            rm += a / 12
        else:
            rm += a

    key = os.getenv("OPENAI_API_KEY")

    if not key:
        return jsonify(
            answer=
            f"Income: ₹{ti:,.2f}\n"
            f"Expenses: ₹{te:,.2f}\n"
            f"Balance: ₹{bal:,.2f}\n"
            f"Recurring: ₹{rm:,.2f}/month"
        )

    try:

        from openai import OpenAI

        client = OpenAI(api_key=key)

        prompt = f"""
You are the AI financial assistant in a personal expense app.

Answer the user's question using ONLY the financial data below.

QUESTION:
{q}

INCOME:
₹{ti:,.2f}

EXPENSES:
₹{te:,.2f}

BALANCE:
₹{bal:,.2f}

MONTHLY RECURRING:
₹{rm:,.2f}

EXPENSE RECORDS:
{e}

INCOME RECORDS:
{inc}

RECURRING:
{rec}

Use Indian Rupees.
Be accurate and practical.
Never invent financial information.
"""

        r = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return jsonify(answer=r.output_text)

    except Exception as ex:

        print("AI ERROR:", repr(ex))

        return jsonify(
            answer="⚠️ AI service error. Please try again later."
        )

# ---------------- RECEIPT SCANNER ----------------

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

        # Keep the complete image data URL.
        image_url = image

        if not image_url.startswith("data:image/"):
            image_url = (
                "data:image/jpeg;base64,"
                + image_url
            )

        prompt = """
You are an expert receipt-reading AI.

Look at the ENTIRE receipt carefully.

Your most important task is to find the
FINAL TOTAL AMOUNT PAID.

Do NOT use:
- individual item prices
- subtotal
- tax alone
- discount
- change
- quantity
- unit price

Use the final grand total / total paid amount.

Also identify:
1. Merchant or short description
2. Category
3. Receipt date

Return ONLY valid JSON.

Exactly this format:

{
  "amount": 123.45,
  "category": "Food",
  "note": "Merchant name",
  "date": "YYYY-MM-DD"
}

CATEGORY MUST BE ONE OF:

Food
Travel
Shopping
Bills
Education
Entertainment
Health
Other

IMPORTANT:

- Carefully zoom mentally into the bottom of the receipt.
- The final total is often near TOTAL, GRAND TOTAL,
  AMOUNT PAID, NET TOTAL or similar.
- Read faint and small digits carefully.
- If there are several totals, choose the final amount paid.
- Do not return 0 unless the receipt genuinely contains
  no readable total.
- Never put ₹ or other currency symbols inside amount.
- If date is visible, convert it to YYYY-MM-DD.
- If date is not visible, use today's date.
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
                            "image_url": image_url
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

        # Remove markdown fences if present.
        text = text.replace(
            "```json", ""
        ).replace(
            "```", ""
        ).strip()

        # Find JSON even if AI added a sentence.
        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if not match:
            raise ValueError(
                "AI did not return valid receipt data."
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

        category = str(
            result.get(
                "category",
                "Other"
            )
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

        if category not in allowed:
            category = "Other"

        note = str(
            result.get(
                "note",
                "Receipt"
            )
        ).strip()

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
            error=
            "Could not read the receipt. "
            "Please take a closer, clearer photo."
        ), 500

@app.route("/api/health")
def health():

    return jsonify(
        success=True,
        message="Smart Expense Tracker is running"
    )

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
