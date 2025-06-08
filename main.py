import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

def get_chatgpt_response(message):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": message}]
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    return response.json()['choices'][0]['message']['content'].strip()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route('/', methods=["GET"])
def index():
    return "Bot is running!"

@app.route('/', methods=["POST"])
def webhook():
    data = request.json

    if data and "message" in data and "text" in data["message"]:
        message = data["message"]["text"]
        chat_id = data["message"]["chat"]["id"]
        reply = get_chatgpt_response(message)
        send_message(chat_id, reply)

    return {"ok": True}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

