from flask import Flask, request
import re
import sqlite3
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = "8773521279:AAHHDihdyGKG9Lcn0x2Oxr31zxQqgfiHlAI"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
ALLOWED_CHATS = [6929050061, 8773521279]

def init_db():
    conn = sqlite3.connect('stock.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hdpe_stock 
                 (item_code TEXT PRIMARY KEY, meters REAL)''')
    conn.commit()
    conn.close()

# YOUR ACTUAL STOCK - UPDATE THESE NUMBERS
HDPE_STOCK = {
    "1.0 inch 8 KG": 1285,
    "1.0 inch 10 KG": 666,
    "1.0 inch 12.5 KG": 863,
    "1.25 inch 8 KG": 274,
    "1.0 inch PE 100 8KG": 87 + 93,  # Combined TUKDE
}

def get_stock():
    conn = sqlite3.connect('stock.db')
    c = conn.cursor()
    c.execute("SELECT item_code, meters FROM hdpe_stock")
    stock = dict(c.fetchall())
    conn.close()
    return stock

def deduct_stock(item_code, meters):
    stock = get_stock()
    if item_code in stock:
        new_stock = max(0, stock[item_code] - meters)
        conn = sqlite3.connect('stock.db')
        c = conn.cursor()
        c.execute("UPDATE hdpe_stock SET meters=? WHERE item_code=?", (new_stock, item_code))
        conn.commit()
        conn.close()
        return new_stock
    return None

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, data={'chat_id': chat_id, 'text': text})

@app.route("/telegram", methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data: return "OK"
    
    chat_id = data['message']['chat']['id']
    if chat_id not in ALLOWED_CHATS: return "OK"
    
    text = data['message'].get('text', '').lower()
    
    # Parse: "93 metre 8 kg PN 100" OR "93 meter pn 100 8 kg"
    pattern = r'(\d+(?:\.\d+)?)\s*(?:meter|metre)\s*(?:pn\s*)?(\d+)\s*(?:kg|kgs?)'
    match = re.search(pattern, text)
    
    if match:
        meters = float(match.group(1))
        pn_size = match.group(2)
        
        # Map to item codes
        item_map = {
            "100": "1.0 inch 8 KG",
            "63": "1.25 inch 8 KG",
            "125": "1.0 inch 12.5 KG"
        }
        
        item_code = item_map.get(pn_size, "1.0 inch 8 KG")
        remaining = deduct_stock(item_code, meters) or HDPE_STOCK.get(item_code, 0) - meters
        
        # EXACT FORMAT YOU WANTED
        response = f"""Sudhakar HDPE : 

PE 100 : 

1.0 inch 8 KG - {get_stock().get('1.0 inch 8 KG', 0):.0f} MTR
1.0 inch 10 KG - {get_stock().get('1.0 inch 10 KG', 0):.0f} MTR
1.0 inch 12.5 KG - {get_stock().get('1.0 inch 12.5 KG', 0):.0f} MTR

PE 63 : 

1.25 inch 8 KG - {get_stock().get('1.25 inch 8 KG', 0):.0f} MTR  (Approx)

TUKDE 

1.0 inch PE 100 8 KG - {get_stock().get('1.0 inch PE 100 8KG', 0):.0f}  MTR"""
        
        send_message(chat_id, response)
        
    elif "/stock" in text:
        stock = get_stock()
        response = f"""Sudhakar HDPE : 

PE 100 : 

1.0 inch 8 KG - {stock.get('1.0 inch 8 KG', 0):.0f} MTR
1.0 inch 10 KG - {stock.get('1.0 inch 10 KG', 0):.0f} MTR
1.0 inch 12.5 KG - {stock.get('1.0 inch 12.5 KG', 0):.0f} MTR

PE 63 : 

1.25 inch 8 KG - {stock.get('1.25 inch 8 KG', 0):.0f} MTR  (Approx)

TUKDE 

1.0 inch PE 100 8 KG - {stock.get('1.0 inch PE 100 8KG', 0):.0f}  MTR"""
        send_message(chat_id, response)
    
    return "OK"

if __name__ == '__main__':
    init_db()
    # Initialize stock
    stock_db = get_stock()
    for item, qty in HDPE_STOCK.items():
        if item not in stock_db:
            conn = sqlite3.connect('stock.db')
            c = conn.cursor()
            c.execute("INSERT INTO hdpe_stock VALUES (?, ?)", (item, qty))
            conn.commit()
            conn.close()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
