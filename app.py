from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "Smart Expense Tracker is running"
    })


if __name__ == "__main__":
    app.run(debug=True)
