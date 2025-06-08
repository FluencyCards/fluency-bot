import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
except KeyError:
    raise RuntimeError("Variável de ambiente TELEGRAM_TOKEN não encontrada.")

try:
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
except KeyError:
    raise RuntimeError("Variável de ambiente OPENAI_API_KEY não encontrada.")

def get_chatgpt_response(message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": message}]
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro na requisição para OpenAI: {str(e)}"
        print(error_msg)
        raise RuntimeError(error_msg)

    try:
        response_json = response.json()
    except ValueError as e:
        error_msg = f"Erro ao decodificar JSON da resposta OpenAI: {str(e)}"
        print(error_msg)
        raise RuntimeError(error_msg)

    try:
        return response_json['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError) as e:
        error_msg = f"Resposta OpenAI inesperada, estrutura incorreta: {str(e)} - Conteúdo: {response_json}"
        print(error_msg)
        raise RuntimeError(error_msg)

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao enviar mensagem para Telegram: {str(e)}"
        print(error_msg)
        raise RuntimeError(error_msg)

@app.route('/', methods=["GET"])
def index():
    return "Bot is running!"

@app.route('/', methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            msg = "Corpo da requisição vazio ou inválido."
            print(msg)
            return jsonify({"ok": False, "error": msg}), 400

        print("🔔 Recebido do Telegram:", data)

        if "message" not in data:
            msg = "'message' não encontrado no payload."
            print(msg)
            return jsonify({"ok": False, "error": msg}), 400

        message_data = data["message"]

        if "text" not in message_data:
            msg = "'text' não encontrado na mensagem."
            print(msg)
            return jsonify({"ok": False, "error": msg}), 400

        message = message_data["text"]
        chat_id = message_data.get("chat", {}).get("id")

        if chat_id is None:
            msg = "'chat id' não encontrado na mensagem."
            print(msg)
            return jsonify({"ok": False, "error": msg}), 400

        print(f"📩 Mensagem recebida: '{message}' | Chat ID: {chat_id}")

        reply = get_chatgpt_response(message)
        print(f"💬 Resposta gerada: '{reply}'")

        send_message(chat_id, reply)
        print("✅ Mensagem enviada com sucesso!")

        return jsonify({"ok": True})

    except RuntimeError as re:
        print("❌ Erro tratado no webhook:", str(re))
        return jsonify({"ok": False, "error": str(re)}), 500
    except Exception as e:
        print("❌ Erro inesperado no webhook:", str(e))
        return jsonify({"ok": False, "error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

