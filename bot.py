import requests
import time
import json
import random
from datetime import datetime
import os

# Configurações
TOKEN = os.getenv("BOT_TOKEN")  # Token vem do .env ou do Railway
URL = f"https://api.telegram.org/bot{TOKEN}/"
DATA_FILE = "user_data.json"

# Inicializar dados
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Verificar se é um novo dia
def is_new_day(last_play_time):
    if not last_play_time:
        return True
    last_play = datetime.fromisoformat(last_play_time)
    now = datetime.now()
    return last_play.date() < now.date()

# Gerar resultado aleatório
def generate_daily_result():
    if random.random() < 0.7:
        return random.randint(1, 10)
    else:
        return random.randint(-5, -1)

# Comando /jogar
def handle_daily_play(user_id, username, chat_id):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {
            "username": username,
            "score": 0,
            "last_play": None,
            "total_plays": 0
        }
    user_data = data[str(user_id)]
    if not is_new_day(user_data["last_play"]):
        return "❌ Você já jogou hoje! Volte amanhã."
    points = generate_daily_result()
    user_data["score"] += points
    user_data["last_play"] = datetime.now().isoformat()
    user_data["total_plays"] += 1
    save_data(data)
    if points > 0:
        message = f"🎉 Parabéns, @{username}! Você ganhou **+{points} pontos**!"
    else:
        message = f"😞 Que pena, @{username}! Você perdeu **{points} pontos**."
    message += f"\n📊 Seu saldo atual: **{user_data['score']} pontos**"
    return message

# Comando /ranking
def get_ranking(chat_id):
    data = load_data()
    if not data:
        return "📊 Ranking vazio. Use /jogar para começar!"
    sorted_users = sorted(data.items(), key=lambda x: x[1]["score"], reverse=True)
    ranking_text = "🏆 **RANKING DO DIA** 🏆\n\n"
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
        medal = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else ""
        ranking_text += f"{medal}{i}º - @{user_data['username']}: **{user_data['score']} pontos**\n"
    return ranking_text

# Comando /meupainel
def get_user_stats(user_id):
    data = load_data()
    user_data = data.get(str(user_id))
    if not user_data:
        return "ℹ️ Use /jogar para começar a participar!"
    username = user_data["username"]
    score = user_data["score"]
    total_plays = user_data["total_plays"]
    last_play = user_data["last_play"]
    last_play_date = datetime.fromisoformat(last_play).strftime("%d/%m/%Y %H:%M") if last_play else "Nunca"
    can_play = is_new_day(last_play)
    status = "✅ Pode jogar hoje!" if can_play else "❌ Já jogou hoje"
    return (f"👤 **Painel de @{username}**\n\n"
            f"📊 Pontuação: **{score} pontos**\n"
            f"🎯 Total de jogadas: **{total_plays}**\n"
            f"🕒 Última jogada: **{last_play_date}**\n"
            f"📅 Status: **{status}**")

# Processar mensagens
def process_message(update):
    if "message" not in update:
        return
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]
    username = message["from"].get("username", f"user_{user_id}")
    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return
    if text.startswith("/jogar"):
        send_message(chat_id, handle_daily_play(user_id, username, chat_id))
    elif text.startswith("/ranking"):
        send_message(chat_id, get_ranking(chat_id))
    elif text.startswith("/meupainel"):
        send_message(chat_id, get_user_stats(user_id))
    elif text.startswith("/start") or text.startswith("/ajuda"):
        send_message(chat_id, "🎮 **BOT DE RANKING DIÁRIO** 🎮\n\n"
                              "/jogar - Jogar uma vez por dia\n"
                              "/ranking - Ver o ranking\n"
                              "/meupainel - Ver suas estatísticas")

# Telegram API
def get_updates(offset=None):
    url = URL + "getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except:
        return {"ok": False, "result": []}

def send_message(chat_id, text):
    url = URL + "sendMessage"
    params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, params=params, timeout=5)
    except:
        pass

# Loop principal
def main():
    print("🤖 Bot de Ranking iniciado...")
    last_update_id = None
    while True:
        try:
            updates = get_updates(last_update_id)
            if updates.get("ok") and "result" in updates:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    process_message(update)
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(5)
        time.sleep(1)

if __name__ == "__main__":
    main()
