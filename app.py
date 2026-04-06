from flask import Flask, request
import re
import sqlite3
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
ALLOWED_CHATS = [6929050061]

DB_NAME = "stock.db"

# DEFAULT STOCK
HDPE_STOCK = {
    "1.0 inch 8 KG": 1285,
    "1.0 inch 10 KG": 666,
    "1.0 inch 12.5 KG": 863,
    "1.25 inch 8 KG": 274,
    "1.0 inch PE 100 8KG": 180,
}

# ---------------- DB ---------------- #
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hdpe_stock 
                 (item_code TEXT PRIMARY KEY, meters REAL)''')

    # Insert default stock if not exists
    for item, qty in HDPE_STOCK.items():
        c.execute("INSERT OR IGNORE INTO hdpe_stock VALUES (?, ?)", (item, qty))

    conn.commit()
    conn.close()


def get_stock():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT item_code, meters FROM hdpe_stock")
    stock = dict(c.fetchall())
    conn.close()
    return stock


def deduct_stock(item_code, meters):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT meters FROM hdpe_stock WHERE item_code=?", (item_code,))
    row = c.fetchone()

    if not row:
        conn.close()
        return None

    current = row[0]
    new_stock = max(0, current - meters)

    c.execute("UPDATE hdpe_stock SET meters=? WHERE item_code=?", (new_stock, item_code))
    conn.commit()
    conn.close()

    return new_stock


# ---------------- TELEGRAM ---------------- #
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    res = requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })
    print(res.text)  # DEBUG


# ---------------- ROUTE ---------------- #
@app.route("/telegram", methods=['POST'])
def webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return "OK"

    chat_id = data["message"]["chat"]["id"]

    if chat_id not in ALLOWED_CHATS:
        return "OK"

    text = data["message"].get("text", "").lower()

    # FLEXIBLE PATTERN (works better)
    pattern = r'(\d+(?:\.\d+)?)\s*(?:m|meter|metre).*?(\d+(?:\.\d+)?)\s*(?:kg)'
    match = re.search(pattern, text)

    if match:
        meters = float(match.group(1))
        kg = match.group(2)

        # Mapping
        item_map = {
            "8": "1.0 inch 8 KG",
            "10": "1.0 inch 10 KG",
            "12.5": "1.0 inch 12.5 KG",
        }

        item_code = item_map.get(kg, "1.0 inch 8 KG")

        deduct_stock(item_code, meters)

        stock = get_stock()

        response = f"""Sudhakar HDPE :

PE 100 :

1.0 inch 8 KG - {stock.get('1.0 inch 8 KG', 0):.0f} MTR
1.0 inch 10 KG - {stock.get('1.0 inch 10 KG', 0):.0f} MTR
1.0 inch 12.5 KG - {stock.get('1.0 inch 12.5 KG', 0):.0f} MTR

PE 63 :

1.25 inch 8 KG - {stock.get('1.25 inch 8 KG', 0):.0f} MTR

TUKDE :

1.0 inch PE 100 8 KG - {stock.get('1.0 inch PE 100 8KG', 0):.0f} MTR"""

        send_message(chat_id, response)

    elif "/stock" in text:
        stock = get_stock()

        response = f"""Sudhakar HDPE :

PE 100 :

1.0 inch 8 KG - {stock.get('1.0 inch 8 KG', 0):.0f} MTR
1.0 inch 10 KG - {stock.get('1.0 inch 10 KG', 0):.0f} MTR
1.0 inch 12.5 KG - {stock.get('1.0 inch 12.5 KG', 0):.0f} MTR

PE 63 :

1.25 inch 8 KG - {stock.get('1.25 inch 8 KG', 0):.0f} MTR

TUKDE :

1.0 inch PE 100 8 KG - {stock.get('1.0 inch PE 100 8KG', 0):.0f} MTR"""

        send_message(chat_id, response)

    return "OK"


# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
