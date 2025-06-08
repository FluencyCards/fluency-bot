import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ----- CONFIGURAÇÃO DAS VARIÁVEIS DE AMBIENTE -----
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Verificação das variáveis críticas
if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN não configurado!")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("❌ DEEPSEEK_API_KEY não configurado!")

# ----- FUNÇÃO OTIMIZADA PARA CHAMAR O DEEPSEEK -----
def get_deepseek_response(user_message):
    endpoint = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    
    except requests.exceptions.Timeout:
        return "⏱️ O tempo de resposta excedeu. Tente novamente!"
    except Exception as e:
        print(f"🚨 Erro DeepSeek: {str(e)}")
        return "⚠️ Ocorreu um erro ao processar sua solicitação."

# ----- ENVIO DE MENSAGENS PARA TELEGRAM -----
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Truncate para evitar limite de 4096 caracteres
    truncated_text = text[:4000] + "..." if len(text) > 4000 else text
    
    payload = {
        "chat_id": chat_id,
        "text": truncated_text,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Erro ao enviar para Telegram: {str(e)}")

# ----- ROTAS -----
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "service": "DeepSeek-Telegram Bot",
        "model": "deepseek-chat"
    })

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        
        # Validação básica do payload
        if 'message' not in data:
            return jsonify({"error": "Formato inválido"}), 400
        
        message = data['message']
        chat_id = message['chat']['id']
        user_text = message.get('text', '').strip()

        # Ignora comandos como /start
        if user_text.startswith('/'):
            return jsonify({"status": "ignored"})

        # Processa a mensagem
        if user_text:
            bot_response = get_deepseek_response(user_text)
            send_telegram_message(chat_id, bot_response)
        
        return jsonify({"status": "processed"})

    except Exception as e:
        print(f"🔥 ERRO CRÍTICO: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# ----- INICIALIZAÇÃO -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
