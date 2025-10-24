import requests
import time
import json
import random
from datetime import datetime
import os
import logging
import psycopg2 
import os

# -------------------
# Configuração de logs
# -------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# -------------------
# Token do bot
# -------------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("BOT_TOKEN não definido! Configure no Railway Settings → Variables")
    exit(1)

URL = f"https://api.telegram.org/bot{TOKEN}/"
DATA_FILE = "user_data.json"

# -------------------
# Funções auxiliares
# -------------------
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
    last_play = datetime.fromisoformat(last_play_time)
    now = datetime.now()
    return last_play.date() < now.date()

def generate_daily_result():
    return random.randint(1, 10) if random.random() < 0.7 else random.randint(-5, -1)

# -------------------
# Comandos do bot
# -------------------
def handle_daily_play(user_id, username, chat_id):
    data = load_data()
    chat_key = str(chat_id)
    user_key = str(user_id)

    if chat_key not in data:
        data[chat_key] = {}
    group_data = data[chat_key]

    if user_key not in group_data:
        group_data[user_key] = {
            "username": username,
            "TAMANHO DA TETA": 0,
            "last_play": None,
            "total_plays": 0
        }

    user_data = group_data[user_key]

    if not is_new_day(user_data["last_play"]):
        return "OH NOJEIRA, TIRA A MÃO DO PEITO! Isso aqui é um grupo de família, volta amanhã!!!!"

    points = generate_daily_result()
    user_data["TAMANHO DA TETA"] += points
    user_data["last_play"] = datetime.now().isoformat()
    user_data["total_plays"] += 1
    save_data(data)

    if points > 0:
        message = f"QUE TETÃO! @{username} VOCÊ GANHOU **+{points} CM DE TETA**!"
    else:
        message = f"Oh dó... @{username} VOCÊ PERDEU **{abs(points)} CM DE TETA**."

    message += f"\nO TAMANHO DA SUA TETA É **{user_data['TAMANHO DA TETA']} CM, PEITUDA METIDA!**"
    return message

def get_ranking(chat_id):
    data = load_data()
    chat_key = str(chat_id)

    if chat_key not in data or not data[chat_key]:
        return "Ranking vazio. Use /jogar para começar!"

    group_data = data[chat_key]
    sorted_users = sorted(group_data.items(), key=lambda x: x[1]["TAMANHO DA TETA"], reverse=True)

    ranking_text = "**RANKING DO DIA**\n\n"
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
        medal = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else ""
        ranking_text += f"{medal}{i}º - @{user_data['username']}: **{user_data['TAMANHO DA TETA']} CM DE TETA**\n"
    return ranking_text

def get_user_stats(user_id, chat_id):
    data = load_data()
    chat_key = str(chat_id)
    user_key = str(user_id)

    if chat_key not in data or user_key not in data[chat_key]:
        return "ℹ️ USE /jogar PARA MEDIR O TAMANHO DESSA SUA TETA"

    user_data = data[chat_key][user_key]
    username = user_data["username"]
    tamanho = user_data["TAMANHO DA TETA"]
    total_plays = user_data["total_plays"]
    last_play = user_data["last_play"]
    last_play_date = datetime.fromisoformat(last_play).strftime("%d/%m/%Y %H:%M") if last_play else "Nunca"
    status = "HORA DE VER SE GANHA OU PERDE" if is_new_day(last_play) else "OH NOJEIRA, TIRA A MÃO DO PEITO! Volte amanhã!"

    return (f"👤 **Tamanho do peito de @{username}**\n\n"
            f"📊 Sua teta é de **{tamanho} CM!**\n"
            f"🎯 Total de jogadas: **{total_plays}**\n"
            f"🕒 Última jogada: **{last_play_date}**\n"
            f"📅 Status: **{status}**")

# -------------------
# Funções Telegram
# -------------------
def send_message(chat_id, text):
    try:
        url = URL + "sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        requests.post(url, params=params, timeout=5)
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem: {e}")

def process_message(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]
    username = message["from"].get("username", f"user_{user_id}")

    logging.info(f"Recebido update de @{username} no chat {chat_id}: {text}")

    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return

    if text.startswith("/jogar"):
        send_message(chat_id, handle_daily_play(user_id, username, chat_id))
    elif text.startswith("/ranking"):
        send_message(chat_id, get_ranking(chat_id))
    elif text.startswith("/meupainel"):
        send_message(chat_id, get_user_stats(user_id, chat_id))
    elif text.startswith("/start") or text.startswith("/ajuda"):
        send_message(chat_id, "🎮 **BOT DE RANKING DIÁRIO** 🎮\n\n"
                              "/jogar - Jogar uma vez por dia\n"
                              "/ranking - Ver o ranking\n"
                              "/meupainel - Ver suas estatísticas")

def get_updates(offset=None):
    url = URL + "getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        logging.error(f"Erro get_updates: {e}")
        return {"ok": False, "result": []}

# -------------------
# Loop principal
# -------------------
def main():
    logging.info("🤖 Bot de Ranking iniciado...")
    last_update_id = None
    while True:
        try:
            updates = get_updates(last_update_id)
            if updates.get("ok") and "result" in updates:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    process_message(update)
        except Exception as e:
            logging.error(f"Erro no loop principal: {e}")
            time.sleep(5)
        time.sleep(1)

if __name__ == "__main__":
    main()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()
