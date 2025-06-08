import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ----- CONFIGURAÇÃO DAS VARIÁVEIS DE AMBIENTE -----
# Defina essas variáveis antes de rodar:
#
# Linux/macOS:
# export TELEGRAM_TOKEN="seu_token_telegram"
# export DEEPSEEK_API_KEY="sua_chave_deepseek"
#
# Windows (PowerShell):
# setx TELEGRAM_TOKEN "seu_token_telegram"
# setx DEEPSEEK_API_KEY "sua_chave_deepseek"
#
# Reinicie o terminal/IDE para aplicar.

try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
except KeyError:
    raise RuntimeError("❌ Variável de ambiente TELEGRAM_TOKEN não encontrada. Defina antes de rodar.")

try:
    DEEPSEEK_API_KEY = os.environ['DEEPSEEK_API_KEY']
except KeyError:
    raise RuntimeError("❌ Variável de ambiente DEEPSEEK_API_KEY não encontrada. Defina antes de rodar.")

# ----- FUNÇÃO PARA CHAMAR A API DEEPSEEK -----
def get_deepseek_response(message):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",  # Ou "deepseek-coder"
        "messages": [{"role": "user", "content": message}]
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()
        response_json = response.json()
        return response_json['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição para DeepSeek: {e}")
        raise RuntimeError(f"Erro na requisição para DeepSeek: {e}")
    except (KeyError, IndexError) as e:
        print(f"❌ Erro ao interpretar resposta DeepSeek: {e} - Resposta: {response_json}")
        raise RuntimeError(f"Erro ao interpretar resposta DeepSeek: {e}")

# ----- FUNÇÃO PARA ENVIAR MENSAGEM PELO TELEGRAM -----
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao enviar mensagem para Telegram: {e}")
        raise RuntimeError(f"Erro ao enviar mensagem para Telegram: {e}")

# ----- ROTA DE TESTE (GET) -----
@app.route('/', methods=["GET"])
def index():
    return "✅ Bot com DeepSeek está rodando!"

# ----- ROTA PARA RECEBER MENSAGENS DO TELEGRAM (POST - WEBHOOK) -----
@app.route('/', methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"ok": False, "error": "Corpo da requisição vazio ou inválido."}), 400

        print("🔔 Recebido do Telegram:", data)

        if "message" not in data:
            return jsonify({"ok": False, "error": "'message' não encontrado no payload."}), 400

        message_data = data["message"]

        if "text" not in message_data:
            return jsonify({"ok": False, "error": "'text' não encontrado na mensagem."}), 400

        message = message_data["text"]
        chat_id = message_data.get("chat", {}).get("id")
        if chat_id is None:
            return jsonify({"ok": False, "error": "'chat id' não encontrado na mensagem."}), 400

        print(f"📩 Mensagem recebida: '{message}' | Chat ID: {chat_id}")

        # Obtém resposta da DeepSeek
        reply = get_deepseek_response(message)
        print(f"💬 Resposta gerada: '{reply}'")

        # Envia resposta para o Telegram
        send_message(chat_id, reply)
        print("✅ Mensagem enviada com sucesso!")

        return jsonify({"ok": True})

    except RuntimeError as e:
        print(f"❌ Erro tratado no webhook: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        print(f"❌ Erro inesperado no webhook: {e}")
        return jsonify({"ok": False, "error": "Erro interno do servidor"}), 500

# ----- INICIAR APP FLASK -----
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

