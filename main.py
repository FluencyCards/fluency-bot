import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ----- CONFIGURAÇÃO DAS VARIÁVEIS DE AMBIENTE -----
# Você deve definir essas variáveis antes de rodar o script:
# No Linux/macOS, no terminal:
# export TELEGRAM_TOKEN="seu_token_do_telegram_aqui"
# export OPENAI_API_KEY="sk-sua_chave_openai_aqui"
#
# No Windows (PowerShell):
# setx TELEGRAM_TOKEN "seu_token_do_telegram_aqui"
# setx OPENAI_API_KEY "sk-sua_chave_openai_aqui"
#
# Depois, reinicie o terminal ou IDE para aplicar as variáveis.
try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
except KeyError:
    raise RuntimeError("Variável de ambiente TELEGRAM_TOKEN não encontrada. Defina antes de rodar.")

try:
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
except KeyError:
    raise RuntimeError("Variável de ambiente OPENAI_API_KEY não encontrada. Defina antes de rodar.")

# ----- FUNÇÃO PARA CHAMAR A API OPENAI -----
def get_chatgpt_response(message):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": message}]
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()  # Levanta exceção para status != 200
        response_json = response.json()
        return response_json['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição para OpenAI: {e}")
        raise RuntimeError(f"Erro na requisição para OpenAI: {e}")
    except (KeyError, IndexError) as e:
        print(f"Erro ao interpretar resposta OpenAI: {e} - Resposta: {response_json}")
        raise RuntimeError(f"Erro ao interpretar resposta OpenAI: {e}")

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
        print(f"Erro ao enviar mensagem para Telegram: {e}")
        raise RuntimeError(f"Erro ao enviar mensagem para Telegram: {e}")

# ----- ROTA PARA TESTE SIMPLES -----
@app.route('/', methods=["GET"])
def index():
    return "Bot está rodando!"

# ----- ROTA PARA RECEBER MENSAGENS DO TELEGRAM (WEBHOOK) -----
@app.route('/', methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"ok": False, "error": "Corpo da requisição vazio ou inválido."}), 400

        print("Recebido do Telegram:", data)

        if "message" not in data:
            return jsonify({"ok": False, "error": "'message' não encontrado no payload."}), 400

        message_data = data["message"]

        if "text" not in message_data:
            return jsonify({"ok": False, "error": "'text' não encontrado na mensagem."}), 400

        message = message_data["text"]
        chat_id = message_data.get("chat", {}).get("id")
        if chat_id is None:
            return jsonify({"ok": False, "error": "'chat id' não encontrado na mensagem."}), 400

        print(f"Mensagem recebida: '{message}' | Chat ID: {chat_id}")

        # Obtém resposta da OpenAI
        reply = get_chatgpt_response(message)
        print(f"Resposta gerada: '{reply}'")

        # Envia resposta para o Telegram
        send_message(chat_id, reply)
        print("Mensagem enviada com sucesso!")

        return jsonify({"ok": True})

    except RuntimeError as e:
        print(f"Erro tratado no webhook: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        print(f"Erro inesperado no webhook: {e}")
        return jsonify({"ok": False, "error": "Erro interno do servidor"}), 500

# ----- RODAR APP -----
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

