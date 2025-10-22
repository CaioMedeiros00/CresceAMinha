import os
import requests
import time
import json
import random
from datetime import datetime
import os


TOKEN = os.getenv("BOT_TOKEN")
# Configurações - Use variáveis de ambiente no Railway!
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8299509958:AAGgE1B_luQeSUgzWYzpsLz-LQlPshMuJdI')
URL = f"https://api.telegram.org/bot{TOKEN}/"
DATA_FILE = "/tmp/user_data.json"  # Usar /tmp no Railway

# ⚠️ REMOVA O TOKEN DO CÓDIGO E USE VARIÁVEIS DE AMBIENTE!

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_new_day(last_play_time):
    if not last_play_time:
        return True
    try:
        last_play = datetime.fromisoformat(last_play_time)
        now = datetime.now()
        return last_play.date() < now.date()
    except:
        return True

def generate_daily_result():
    if random.random() < 0.7:
        return random.randint(1, 100)
    else:
        return random.randint(-50, -1)

def handle_daily_play(user_id, username, first_name, chat_id):
    data = load_data()
    
    display_name = f"@{username}" if username else first_name
    
    if str(user_id) not in data:
        data[str(user_id)] = {
            "username": username,
            "first_name": first_name,
            "score": 0,
            "last_play": None,
            "total_plays": 0
        }
    
    user_data = data[str(user_id)]
    
    if not is_new_day(user_data["last_play"]):
        return f"❌ {display_name}, você já jogou hoje! Volte amanhã."
    
    points = generate_daily_result()
    user_data["score"] += points
    user_data["last_play"] = datetime.now().isoformat()
    user_data["total_plays"] += 1
    
    save_data(data)
    
    if points > 0:
        message = f"🎉 {display_name}! Ganhou **+{points} pontos**!"
    else:
        message = f"😞 {display_name}! Perdeu **{points} pontos**."
    
    message += f"\n📊 Saldo: **{user_data['score']} pontos**"
    return message

def get_ranking():
    data = load_data()
    
    if not data:
        return "📊 Ranking vazio. Use /jogar para começar!"
    
    sorted_users = sorted(data.items(), key=lambda x: x[1]["score"], reverse=True)
    
    ranking_text = "🏆 **RANKING** 🏆\n\n"
    
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "🏅"
        username = user_data.get("username")
        first_name = user_data.get("first_name", "Usuário")
        display_name = f"@{username}" if username else first_name
        score = user_data["score"]
        ranking_text += f"{medal} {i}º - {display_name}: **{score} pts**\n"
    
    return ranking_text

def get_user_stats(user_id):
    data = load_data()
    user_data = data.get(str(user_id))
    
    if not user_data:
        return "ℹ️ Use /jogar para começar!"
    
    username = user_data.get("username")
    first_name = user_data.get("first_name", "Usuário")
    display_name = f"@{username}" if username else first_name
    score = user_data["score"]
    total_plays = user_data["total_plays"]
    last_play = user_data["last_play"]
    
    if last_play:
        last_play_date = datetime.fromisoformat(last_play).strftime("%d/%m/%Y")
    else:
        last_play_date = "Nunca"
    
    message = f"👤 **Painel de {display_name}**\n\n"
    message += f"📊 Pontuação: **{score} pontos**\n"
    message += f"🎯 Total de jogadas: **{total_plays}**\n"
    message += f"🕒 Última jogada: **{last_play_date}**\n"
    
    can_play = is_new_day(last_play)
    status = "✅ Pode jogar hoje!" if can_play else "❌ Já jogou hoje"
    message += f"📅 Status: **{status}**"
    
    return message

def send_message(chat_id, text):
    url = URL + "sendMessage"
    params = {
        "chat_id": chat_id, 
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, params=params, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def get_updates(offset=None):
    url = URL + "getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar updates: {e}")
        return {"ok": False, "result": []}

def process_message(update):
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]
    username = message["from"].get("username")
    first_name = message["from"].get("first_name", "Usuário")
    
    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return
    
    if text.startswith("/jogar"):
        response = handle_daily_play(user_id, username, first_name, chat_id)
        send_message(chat_id, response)
    
    elif text.startswith("/ranking"):
        response = get_ranking()
        send_message(chat_id, response)
    
    elif text.startswith("/meupainel"):
        response = get_user_stats(user_id)
        send_message(chat_id, response)
    
    elif text.startswith("/start") or text.startswith("/ajuda"):
        help_text = """🎮 **BOT DE RANKING DIÁRIO** 🎮

Comandos:
/jogar - Jogue uma vez por dia
/ranking - Ver ranking
/meupainel - Suas estatísticas

📝 **Regras:**
- Uma jogada por dia
- Ganhe ou perca pontos
- Compita com amigos!"""
        send_message(chat_id, help_text)

def main():
    print("🤖 Bot iniciado...")
    last_update_id = None
    
    while True:
        try:
            updates = get_updates(last_update_id)
            
            if updates.get("ok") and "result" in updates:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    process_message(update)
        
        except Exception as e:
            print(f"Erro geral: {e}")
            time.sleep(10)
        
        time.sleep(1)

if __name__ == "__main__":
    main()