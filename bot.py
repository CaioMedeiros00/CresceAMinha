import requests
import time
import random
from datetime import datetime
import os
import logging
import pg8000

# -------------------
# Configuração de logs
# -------------------
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------
# Token do bot
# -------------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN não definido!")
    exit(1)

URL = f"https://api.telegram.org/bot{TOKEN}/"

# -------------------
# Conexão com PostgreSQL usando pg8000
# -------------------
def get_db_connection():
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            logger.error("DATABASE_URL não definido!")
            return None
        
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        from urllib.parse import urlparse
        url = urlparse(DATABASE_URL)
        
        conn = pg8000.connect(
            host=url.hostname,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database=url.path[1:]
        )
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar com PostgreSQL: {e}")
        return None

def init_db():
    max_retries = 3
    for attempt in range(max_retries):
        conn = get_db_connection()
        if not conn:
            logger.error(f"Tentativa {attempt+1} falhou")
            time.sleep(2)
            continue
        try:
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
            cur.execute('''
                CREATE TABLE IF NOT EXISTS duelos (
                    id SERIAL PRIMARY KEY,
                    challenger_id BIGINT NOT NULL,
                    defender_id BIGINT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pendente',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar banco (tentativa {attempt+1}): {e}")
            if conn:
                conn.close()
            time.sleep(2)
    return False

# -------------------
# Funções auxiliares
# -------------------
def is_new_day(last_play_time):
    if not last_play_time:
        return True
    try:
        if isinstance(last_play_time, str):
            last_play = datetime.fromisoformat(last_play_time.replace('Z', '+00:00'))
        else:
            last_play = last_play_time
        now = datetime.now()
        return last_play.date() < now.date()
    except Exception as e:
        logger.error(f"Erro em is_new_day: {e}")
        return True

def generate_daily_result():
    return random.randint(1, 10) if random.random() < 0.7 else random.randint(-5, -1)

def execute_sql(query, params=None, fetch=False):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        result = cur.fetchall() if fetch else True
        conn.commit()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Erro SQL: {e} - Query: {query} - Params: {params}")
        if conn:
            conn.close()
        return None

# -------------------
# Frases personalizadas
# -------------------
WIN_PHRASES = [
    "SUA TETA EXPLODIU DE TAMANHO!",
    "O UNIVERSO CONSPIRA A FAVOR DA SUA TETA!",
    "A FORÇA ESTÁ COM SUA TETA!",
    "HOJE É DIA DE PEITO!",
    "CRESCIMENTO APROVADO PELO MINISTÉRIO DA TETA!",
]

LOSE_PHRASES = [
    "SUA TETA MURCHOU IGUAL AOS SEUS SONHOS.",
    "NÃO DA PRA GANHAR SEMPRE, MAS PERDER DÁ",
    "SUA TETA PEDIU ARREGO!",
    "RESULTADO NEGATIVO, MAS AMANHÃ É OUTRO DIA!",
    "TETA FRAQUEINHA FRAQUINHA...",
]

# -------------------
# Funções do jogo
# -------------------
def handle_daily_play(user_id, username, chat_id):
    result = execute_sql(
        'SELECT tamanho_teta, last_play, total_plays FROM player_tetas WHERE user_id=%s AND chat_id=%s',
        (user_id, chat_id),
        fetch=True
    )
    points = generate_daily_result()
    if result:
        tamanho_teta, last_play, total_plays = result[0]
        if not is_new_day(last_play):
            return "OH NOJEIRA, TIRA A MÃO DO PEITO! Volte amanhã!!!!"
        novo_tamanho = tamanho_teta + points
        novo_total_plays = total_plays + 1
        success = execute_sql(
            '''UPDATE player_tetas SET tamanho_teta=%s, last_play=CURRENT_TIMESTAMP, total_plays=%s,
               username=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s AND chat_id=%s''',
            (novo_tamanho, novo_total_plays, username, user_id, chat_id)
        )
    else:
        novo_tamanho = points
        novo_total_plays = 1
        success = execute_sql(
            '''INSERT INTO player_tetas (user_id, chat_id, username, tamanho_teta, last_play, total_plays)
               VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP,%s)''',
            (user_id, chat_id, username, novo_tamanho, novo_total_plays)
        )

    logger.info(f"User: {username}, Points: {points}, Success: {success}")

    if success is None:
        return "❌ Erro ao salvar os dados. Tente novamente!"

    phrase = random.choice(WIN_PHRASES if points > 0 else LOSE_PHRASES)
    message = f"{phrase}\n"
    message += f"O TAMANHO DA SUA TETA É **{novo_tamanho} CM, PEITUDA METIDA!**"
    return message

def get_ranking(chat_id):
    result = execute_sql(
        'SELECT username, tamanho_teta FROM player_tetas WHERE chat_id=%s ORDER BY tamanho_teta DESC LIMIT 10',
        (chat_id,), fetch=True
    )
    if not result:
        return "Ranking vazio. Use /jogar para começar!"
    text = "**RANKING DO DIA**\n\n"
    for i, (username, tamanho) in enumerate(result, 1):
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else ""
        username_display = f"@{username}" if username else "Usuário Anônimo"
        text += f"{medal}{i}º - {username_display}: **{tamanho} CM**\n"
    return text

def get_user_stats(user_id, chat_id):
    result = execute_sql(
        'SELECT username, tamanho_teta, total_plays, last_play FROM player_tetas WHERE user_id=%s AND chat_id=%s',
        (user_id, chat_id), fetch=True
    )
    if not result:
        return "ℹ️ USE /jogar PARA MEDIR O TAMANHO DESSA SUA TETA"
    username, tamanho, total_plays, last_play = result[0]
    last_play_date = last_play.strftime("%d/%m/%Y %H:%M") if last_play else "Nunca"
    status = "HORA DE VER SE GANHA OU PERDE" if is_new_day(last_play) else "OH NOJEIRA, TIRA A MÃO DO PEITO! Volte amanhã!"
    return (f"👤 **Tamanho do peito de @{username}**\n\n"
            f"📊 Sua teta é de **{tamanho} CM!**\n"
            f"🎯 Total de jogadas: **{total_plays}**\n"
            f"🕒 Última jogada: **{last_play_date}**\n"
            f"📅 Status: **{status}**")

# -------------------
# Doar teta
# -------------------
def donate_teta(donor_id, target_username, chat_id, amount, reply_user_id=None):
    target_id = None
    if target_username:
        res = execute_sql(
            'SELECT user_id FROM player_tetas WHERE username=%s AND chat_id=%s',
            (target_username, chat_id), fetch=True
        )
        if res:
            target_id = res[0][0]
    elif reply_user_id:
        target_id = reply_user_id

    if not target_id or target_id == donor_id:
        return "❌ Alvo inválido para doação!"

    donor_data = execute_sql('SELECT tamanho_teta FROM player_tetas WHERE user_id=%s AND chat_id=%s',
                             (donor_id, chat_id), fetch=True)
    target_data = execute_sql('SELECT tamanho_teta FROM player_tetas WHERE user_id=%s AND chat_id=%s',
                              (target_id, chat_id), fetch=True)
    if not donor_data or not target_data:
        return "❌ Ambos precisam ter jogado pelo menos uma vez!"

    donor_teta = donor_data[0][0]
    if donor_teta < amount:
        return "❌ Você não tem teta suficiente para doar!"

    execute_sql('UPDATE player_tetas SET tamanho_teta=tamanho_teta-%s WHERE user_id=%s AND chat_id=%s',
                (amount, donor_id, chat_id))
    execute_sql('UPDATE player_tetas SET tamanho_teta=tamanho_teta+%s WHERE user_id=%s AND chat_id=%s',
                (amount, target_id, chat_id))
    return f"🎁 Doação concluída! {amount} CM de teta foram doados."

# -------------------
# Duelo
# -------------------
def start_duel(challenger_id, target_username, chat_id):
    target_data = execute_sql(
        'SELECT user_id FROM player_tetas WHERE username=%s AND chat_id=%s',
        (target_username, chat_id), fetch=True
    )
    if not target_data:
        return "❌ Jogador não encontrado!"
    defender_id = target_data[0][0]
    if defender_id == challenger_id:
        return "❌ Não pode duelar consigo mesmo!"
    # Cria duelo pendente
    execute_sql(
        'INSERT INTO duelos (challenger_id, defender_id) VALUES (%s,%s)',
        (challenger_id, defender_id)
    )
    return f"⚔️ Duelo iniciado contra @{target_username}! Ele precisa aceitar com /aceitar"

def accept_duel(user_id, chat_id):
    res = execute_sql(
        'SELECT id, challenger_id, defender_id FROM duelos WHERE defender_id=%s AND status=%s ORDER BY created_at ASC LIMIT 1',
        (user_id, 'pendente'), fetch=True
    )
    if not res:
        return "❌ Nenhum duelo pendente!"
    duel_id, challenger_id, defender_id = res[0]

    challenger_data = execute_sql(
        'SELECT username FROM player_tetas WHERE user_id=%s AND chat_id=%s',
        (challenger_id, chat_id), fetch=True
    )
    defender_data = execute_sql(
        'SELECT username FROM player_tetas WHERE user_id=%s AND chat_id=%s',
        (defender_id, chat_id), fetch=True
    )
    if not challenger_data or not defender_data:
        return "❌ Um dos jogadores não está registrado!"

    challenger_name = challenger_data[0][0]
    defender_name = defender_data[0][0]

    winner_id, loser_id = random.choice([(challenger_id, defender_id), (defender_id, challenger_id)])
    winner_name = challenger_name if winner_id == challenger_id else defender_name
    loser_name = defender_name if loser_id == defender_id else challenger_name

    gain = random.randint(5, 15)
    loss = random.randint(1, 10)
    execute_sql('UPDATE player_tetas SET tamanho_teta=tamanho_teta+%s WHERE user_id=%s AND chat_id=%s',
                (gain, winner_id, chat_id))
    execute_sql('UPDATE player_tetas SET tamanho_teta=GREATEST(tamanho_teta-%s,0) WHERE user_id=%s AND chat_id=%s',
                (loss, loser_id, chat_id))
    execute_sql('UPDATE duelos SET status=%s WHERE id=%s', ('concluido', duel_id))

    return (f"🏆 @{winner_name} venceu o duelo contra @{loser_name}!\n"
            f"🎉 Ganhou +{gain} CM de teta!\n"
            f"😢 @{loser_name} perdeu -{loss} CM de teta.")

# -------------------
# Funções Telegram
# -------------------
def send_message(chat_id, text):
    try:
        url = URL + "sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")

def process_message(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]
    username = message["from"].get("username", f"user_{user_id}")
    reply_user_id = message.get("reply_to_message", {}).get("from", {}).get("id")

    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return

    try:
        if text.startswith("/jogar"):
            send_message(chat_id, handle_daily_play(user_id, username, chat_id))
        elif text.startswith("/ranking"):
            send_message(chat_id, get_ranking(chat_id))
        elif text.startswith("/meupainel"):
            send_message(chat_id, get_user_stats(user_id, chat_id))
        elif text.startswith("/doar"):
            parts = text.split()
            target = parts[1][1:] if len(parts) >= 3 and parts[1].startswith("@") else None
            try:
                amount = int(parts[-1])
            except:
                send_message(chat_id, "❌ Valor inválido.")
                return
            send_message(chat_id, donate_teta(user_id, target, chat_id, amount, reply_user_id))
        elif text.startswith("/duelar") or text.startswith("/duelo"):
            parts = text.split()
            if len(parts) < 2 or not parts[1].startswith("@"):
                send_message(chat_id, "❌ Use /duelar @usuario")
            else:
                target_username = parts[1][1:]
                send_message(chat_id, start_duel(user_id, target_username, chat_id))
        elif text.startswith("/aceitar"):
            send_message(chat_id, accept_duel(user_id, chat_id))
        elif text.startswith("/start") or text.startswith("/ajuda"):
            send_message(chat_id, "🎮 **BOT DE RANKING DIÁRIO** 🎮\n\n"
                                 "/jogar - Jogar uma vez por dia\n"
                                 "/ranking - Ver o ranking\n"
                                 "/meupainel - Ver suas estatísticas\n"
                                 "/doar @usuario valor - Doar teta\n"
                                 "/duelar @usuario - Iniciar duelo\n"
                                 "/aceitar - Aceitar duelo pendente")
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        send_message(chat_id, "❌ Ocorreu um erro interno. Tente novamente mais tarde.")

def get_updates(offset=None):
    url = URL + "getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"Erro get_updates: {e}")
        return {"ok": False, "result": []}

# -------------------
# Loop principal
# -------------------
def main():
    logger.info("Iniciando bot...")
    if not init_db():
        logger.error("Falha ao inicializar banco. Encerrando.")
        return

    logger.info("🤖 Bot iniciado com sucesso!")
    last_update_id = None
    error_count = 0
    max_errors = 5

    while True:
        try:
            updates = get_updates(last_update_id)
            if updates.get("ok"):
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    process_message(update)
                error_count = 0
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            error_count += 1
            time.sleep(5)

        if error_count >= max_errors:
            logger.error("Muitos erros consecutivos. Aguardando 30s...")
            time.sleep(30)
            error_count = 0

        time.sleep(1)

if __name__ == "__main__":
    main()
