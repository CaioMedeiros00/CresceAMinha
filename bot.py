import requests
import time
import json
import random
from datetime import datetime
import os
import logging
import psycopg2

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

# -------------------
# Conexão com PostgreSQL
# -------------------
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Inicializa o banco de dados criando a tabela se não existir"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS player_tetas (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            username VARCHAR(100),
            tamanho_teta INTEGER DEFAULT 0,
            last_play TIMESTAMP,
            total_plays INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chat_id)
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    logging.info("Banco de dados inicializado!")

# -------------------
# Funções auxiliares
# -------------------
def is_new_day(last_play_time):
    if not last_play_time:
        return True
    last_play = last_play_time if isinstance(last_play_time, datetime) else datetime.fromisoformat(last_play_time)
    now = datetime.now()
    return last_play.date() < now.date()

def generate_daily_result():
    return random.randint(1, 10) if random.random() < 0.7 else random.randint(-5, -1)

# -------------------
# Comandos do bot (AGORA COM POSTGRES)
# -------------------
def handle_daily_play(user_id, username, chat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Busca ou cria o usuário
    cur.execute('''
        SELECT tamanho_teta, last_play, total_plays 
        FROM player_tetas 
        WHERE user_id = %s AND chat_id = %s
    ''', (user_id, chat_id))
    
    result = cur.fetchone()
    
    if result:
        tamanho_teta, last_play, total_plays = result
        
        # Verifica se já jogou hoje
        if not is_new_day(last_play):
            cur.close()
            conn.close()
            return "OH NOJEIRA, TIRA A MÃO DO PEITO! Isso aqui é um grupo de família, volta amanhã!!!!"
        
        points = generate_daily_result()
        novo_tamanho = tamanho_teta + points
        novo_total_plays = total_plays + 1
        
        # Atualiza o registro
        cur.execute('''
            UPDATE player_tetas 
            SET tamanho_teta = %s, last_play = CURRENT_TIMESTAMP, total_plays = %s, 
                username = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND chat_id = %s
        ''', (novo_tamanho, novo_total_plays, username, user_id, chat_id))
        
    else:
        # Primeira jogada do usuário
        points = generate_daily_result()
        novo_tamanho = points
        novo_total_plays = 1
        
        # Insere novo registro
        cur.execute('''
            INSERT INTO player_tetas (user_id, chat_id, username, tamanho_teta, last_play, total_plays)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        ''', (user_id, chat_id, username, novo_tamanho, novo_total_plays))
    
    conn.commit()
    cur.close()
    conn.close()
    
    if points > 0:
        message = f"QUE TETÃO! @{username} VOCÊ GANHOU **+{points} CM DE TETA**!"
    else:
        message = f"Oh dó... @{username} VOCÊ PERDEU **{abs(points)} CM DE TETA**."

    message += f"\nO TAMANHO DA SUA TETA É **{novo_tamanho} CM, PEITUDA METIDA!**"
    return message

def get_ranking(chat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT username, tamanho_teta 
        FROM player_tetas 
        WHERE chat_id = %s 
        ORDER BY tamanho_teta DESC 
        LIMIT 10
    ''', (chat_id,))
    
    ranking = cur.fetchall()
    cur.close()
    conn.close()
    
    if not ranking:
        return "Ranking vazio. Use /jogar para começar!"

    ranking_text = "**RANKING DO DIA**\n\n"
    for i, (username, tamanho_teta) in enumerate(ranking, 1):
        medal = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else ""
        username_display = f"@{username}" if username else "Usuário Anônimo"
        ranking_text += f"{medal}{i}º - {username_display}: **{tamanho_teta} CM DE TETA**\n"
    
    return ranking_text

def get_user_stats(user_id, chat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT username, tamanho_teta, total_plays, last_play 
        FROM player_tetas 
        WHERE user_id = %s AND chat_id = %s
    ''', (user_id, chat_id))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if not result:
        return "ℹ️ USE /jogar PARA MEDIR O TAMANHO DESSA SUA TETA"

    username, tamanho, total_plays, last_play = result
    
    last_play_date = last_play.strftime("%d/%m/%Y %H:%M") if last_play else "Nunca"
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
    # Inicializa o banco de dados
    init_db()
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