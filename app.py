from flask import Flask, send_from_directory, jsonify, request
import sqlite3, os, base64, json

app=Flask(__name__)
DB="expenses.db"

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL, category TEXT NOT NULL,
        note TEXT, date TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS income(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL, source TEXT NOT NULL,
        date TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS recurring(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, amount REAL NOT NULL,
        frequency TEXT NOT NULL, next_date TEXT NOT NULL)""")
    c.commit(); c.close()

init_db()

@app.route("/")
def home(): return send_from_directory(".", "index.html")

@app.route("/analytics.html")
def analytics(): return send_from_directory(".", "analytics.html")

@app.route("/goals.html")
def goals(): return send_from_directory(".", "goals.html")

@app.route("/recurring.html")
def recurring(): return send_from_directory(".", "recurring.html")

@app.route("/api/expenses")
def expenses():
    c=db()
    r=c.execute("SELECT * FROM expenses ORDER BY date DESC,id DESC").fetchall()
    c.close()
    return jsonify([dict(x) for x in r])

@app.route("/api/expenses",methods=["POST"])
def add_expense():
    d=request.get_json() or {}
    if not d.get("amount") or not d.get("category") or not d.get("date"):
        return jsonify(success=False,error="Please fill all required fields."),400
    c=db()
    x=c.execute("""INSERT INTO expenses(amount,category,note,date)
                   VALUES(?,?,?,?)""",
                (float(d["amount"]),d["category"],d.get("note",""),d["date"]))
    c.commit(); i=x.lastrowid; c.close()
    return jsonify(success=True,id=i)

@app.route("/api/expenses/<int:i>",methods=["DELETE"])
def delete_expense(i):
    c=db(); c.execute("DELETE FROM expenses WHERE id=?",(i,))
    c.commit(); c.close()
    return jsonify(success=True)

@app.route("/api/income")
def income():
    c=db()
    r=c.execute("SELECT * FROM income ORDER BY date DESC,id DESC").fetchall()
    c.close()
    return jsonify([dict(x) for x in r])

@app.route("/api/income",methods=["POST"])
def add_income():
    d=request.get_json() or {}
    if not d.get("amount") or not d.get("source") or not d.get("date"):
        return jsonify(success=False,error="Please fill all income fields."),400
    c=db()
    x=c.execute("""INSERT INTO income(amount,source,date)
                   VALUES(?,?,?)""",
                (float(d["amount"]),d["source"],d["date"]))
    c.commit(); i=x.lastrowid; c.close()
    return jsonify(success=True,id=i)

@app.route("/api/income/<int:i>",methods=["DELETE"])
def delete_income(i):
    c=db(); c.execute("DELETE FROM income WHERE id=?",(i,))
    c.commit(); c.close()
    return jsonify(success=True)

@app.route("/api/financial-summary")
def summary():
    c=db()
    inc=c.execute("SELECT COALESCE(SUM(amount),0) x FROM income").fetchone()["x"]
    exp=c.execute("SELECT COALESCE(SUM(amount),0) x FROM expenses").fetchone()["x"]
    rec=c.execute("SELECT COALESCE(SUM(amount),0) x FROM recurring").fetchone()["x"]
    c.close()
    return jsonify(income=float(inc),expenses=float(exp),
                   balance=float(inc-exp),recurring=float(rec))

@app.route("/api/recurring")
def get_recurring():
    c=db()
    r=c.execute("SELECT * FROM recurring ORDER BY next_date").fetchall()
    c.close()
    return jsonify([dict(x) for x in r])

@app.route("/api/recurring",methods=["POST"])
def add_recurring():
    d=request.get_json() or {}
    if not d.get("name") or not d.get("amount") or not d.get("next_date"):
        return jsonify(success=False,error="Please fill all recurring payment fields."),400
    c=db()
    x=c.execute("""INSERT INTO recurring
                   (name,amount,frequency,next_date)
                   VALUES(?,?,?,?)""",
                (d["name"],float(d["amount"]),
                 d.get("frequency","monthly"),d["next_date"]))
    c.commit(); i=x.lastrowid; c.close()
    return jsonify(success=True,id=i)

@app.route("/api/recurring/<int:i>",methods=["DELETE"])
def delete_recurring(i):
    c=db(); c.execute("DELETE FROM recurring WHERE id=?",(i,))
    c.commit(); c.close()
    return jsonify(success=True)

def financial_data():
    c=db()
    e=[dict(x) for x in c.execute(
        "SELECT amount,category,note,date FROM expenses ORDER BY date DESC").fetchall()]
    inc=[dict(x) for x in c.execute(
        "SELECT amount,source,date FROM income ORDER BY date DESC").fetchall()]
    rec=[dict(x) for x in c.execute(
        "SELECT name,amount,frequency,next_date FROM recurring ORDER BY next_date").fetchall()]
    c.close()
    return e,inc,rec

@app.route("/api/ai",methods=["POST"])
def ai():
    d=request.get_json() or {}
    q=d.get("question","").strip()
    if not q:return jsonify(answer="Please enter a question."),400

    e,inc,rec=financial_data()
    te=sum(float(x["amount"]) for x in e)
    ti=sum(float(x["amount"]) for x in inc)
    bal=ti-te
    rm=0
    for x in rec:
        a=float(x["amount"])
        rm+=a*52/12 if x["frequency"]=="weekly" else a/12 if x["frequency"]=="yearly" else a

    cats={}
    for x in e:
        cats[x["category"]]=cats.get(x["category"],0)+float(x["amount"])

    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return jsonify(answer=f"Income: ₹{ti:,.2f}\nExpenses: ₹{te:,.2f}\nBalance: ₹{bal:,.2f}\nRecurring: ₹{rm:,.2f}/month")

    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        prompt=f"""You are the AI financial assistant in a personal expense app.
Answer the user's question using ONLY this data.

QUESTION:
{q}

INCOME: ₹{ti:,.2f}
EXPENSES: ₹{te:,.2f}
BALANCE: ₹{bal:,.2f}
MONTHLY RECURRING: ₹{rm:,.2f}
CATEGORIES: {cats}
EXPENSES: {e}
INCOME RECORDS: {inc}
RECURRING: {rec}

Use Indian Rupees. Be practical, accurate and reasonably short.
Never invent financial information."""
        r=client.responses.create(model="gpt-5.6-luna",input=prompt)
        return jsonify(answer=r.output_text)
    except Exception as ex:
        print("AI ERROR:",repr(ex))
        return jsonify(answer="⚠️ AI service error. Please try again later.")

# ---------- AI RECEIPT SCANNER ----------

@app.route("/api/scan-receipt",methods=["POST"])
def scan_receipt():
    d=request.get_json() or {}
    image=d.get("image","")

    if not image:
        return jsonify(success=False,error="Please upload a receipt image."),400

    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return jsonify(success=False,error="AI service is not configured."),500

    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)

        if "," in image:
            image=image.split(",",1)[1]

        prompt="""Read this receipt and extract the financial information.

Return ONLY valid JSON in exactly this format:
{
  "amount": 0,
  "category": "Food",
  "note": "merchant or short description",
  "date": "YYYY-MM-DD"
}

Rules:
- amount must be the final total paid.
- category must be one of:
Food, Travel, Shopping, Bills, Education,
Entertainment, Health, Other.
- If the date is visible, convert it to YYYY-MM-DD.
- If the date is not visible, use today's date.
- Never invent an amount.
- If the amount cannot be confidently read, use 0.
"""

        response=client.responses.create(
            model="gpt-5.6-luna",
            input=[{
                "role":"user",
                "content":[
                    {"type":"input_text","text":prompt},
                    {"type":"input_image",
                     "image_url":"data:image/jpeg;base64,"+image}
                ]
            }]
        )

        text=response.output_text.strip()
        text=text.replace("```json","").replace("```","").strip()
        result=json.loads(text)

        return jsonify(
            success=True,
            amount=result.get("amount",0),
            category=result.get("category","Other"),
            note=result.get("note","Receipt"),
            date=result.get("date","")
        )

    except Exception as ex:
        print("RECEIPT ERROR:",repr(ex))
        return jsonify(
            success=False,
            error="Could not read this receipt. Try a clearer photo."
        ),500

@app.route("/api/health")
def health():
    return jsonify(success=True,message="Smart Expense Tracker is running")

if __name__=="__main__":
    app.run(host="0.0.0.0",
            port=int(os.environ.get("PORT",5000)))
