import requests
import time
import random
from datetime import datetime
import os
import logging
import pg8000
from urllib.parse import urlparse
import ssl

# -------------------
# Configuração de logs
# -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------
# Config (env) - VERIFIQUE SE O TOKEN ESTÁ CONFIGURADO!
# -------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("❌ NENHUM TOKEN ENCONTRADO! Configure TELEGRAM_TOKEN ou BOT_TOKEN")
    exit(1)

URL = f"https://api.telegram.org/bot{TOKEN}/"
logger.info(f"Token configurado, URL base: {URL[:50]}...")

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados Postgres"""
    try:
        database_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_RO")
        
        if database_url:
            parsed = urlparse(database_url)
            host = parsed.hostname
            user = parsed.username
            password = parsed.password
            database = parsed.path.lstrip("/")
            port = parsed.port or 5432

            # Tenta conectar com SSL para Railway
            try:
                ssl_ctx = ssl.create_default_context()
                conn = pg8000.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    port=port,
                    ssl_context=ssl_ctx,
                )
            except Exception as e:
                logger.warning(f"Tentando conexão SSL alternativa: {e}")
                conn = pg8000.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    port=port,
                    ssl=True,
                )
            return conn

        # Fallback para variáveis individuais
        host = os.environ.get("PGHOST")
        user = os.environ.get("PGUSER")
        password = os.environ.get("PGPASSWORD")
        database = os.environ.get("PGDATABASE")
        port = int(os.environ.get("PGPORT", "5432"))

        if all([host, user, password, database]):
            return pg8000.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port,
            )

        logger.error("❌ Nenhuma configuração de banco de dados encontrada")
        return None

    except Exception as e:
        logger.error(f"❌ Erro na conexão com o banco: {e}")
        return None

def init_db(retries: int = 3):
    """Garante que a tabela exista"""
    for attempt in range(1, retries + 1):
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                raise Exception("Falha ao conectar com o banco")
            
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS player_tetas (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    tamanho_teta INTEGER DEFAULT 0,
                    last_play TIMESTAMP,
                    total_plays INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            ''')
            conn.commit()
            logger.info("✅ Tabela player_tetas verificada/criada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco (tentativa {attempt}): {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            time.sleep(2)
    
    return False

def is_new_day(last_play_time):
    """Verifica se já passou um dia desde a última jogada"""
    if not last_play_time:
        return True
    try:
        if isinstance(last_play_time, str):
            last_play = datetime.fromisoformat(last_play_time.replace('Z', '+00:00'))
        else:
            last_play = last_play_time
        return last_play.date() < datetime.now().date()
    except Exception as e:
        logger.error(f"Erro em is_new_day: {e}")
        return True

def generate_daily_result():
    """Gera resultado diário: 70% chance positivo, 30% negativo"""
    return random.randint(1, 10) if random.random() < 0.7 else random.randint(-5, -1)

def execute_sql(query, params=None, fetch=False):
    """Executa query SQL com tratamento de erro"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        
        if fetch:
            result = cur.fetchall()
        else:
            result = True
            
        conn.commit()
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro SQL: {e} - Query: {query}")
        return None
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

# --- COMANDOS DO BOT ---
def handle_daily_play(user_id, username, chat_id):
    """Processa a jogada diária do usuário"""
    result = execute_sql(
        'SELECT tamanho_teta, last_play, total_plays FROM player_tetas WHERE user_id = %s AND chat_id = %s',
        (user_id, chat_id),
        fetch=True
    )
    
    if result is None:
        return "❌ Erro no banco de dados. Tente novamente mais tarde."
    
    points = generate_daily_result()
    
    if result:
        # Usuário existe
        tamanho_teta, last_play, total_plays = result[0]
        
        if not is_new_day(last_play):
            return "OH NOJEIRA, TIRA A MÃO DO PEITO! Isso aqui é um grupo de família, volta amanhã!!!!"
        
        novo_tamanho = tamanho_teta + points
        novo_total_plays = total_plays + 1
        
        success = execute_sql(
            '''UPDATE player_tetas 
               SET tamanho_teta = %s, last_play = CURRENT_TIMESTAMP, total_plays = %s, 
                   username = %s, updated_at = CURRENT_TIMESTAMP
               WHERE user_id = %s AND chat_id = %s''',
            (novo_tamanho, novo_total_plays, username, user_id, chat_id)
        )
    else:
        # Novo usuário
        novo_tamanho = points
        novo_total_plays = 1
        
        success = execute_sql(
            '''INSERT INTO player_tetas (user_id, chat_id, username, tamanho_teta, last_play, total_plays)
               VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)''',
            (user_id, chat_id, username, novo_tamanho, novo_total_plays)
        )
    
    if not success:
        return "❌ Erro ao salvar os dados. Tente novamente!"
    
    if points > 0:
        message = f"QUE TETÃO! @{username} VOCÊ GANHOU **+{points} CM DE TETA**!"
    else:
        message = f"Oh dó... @{username} VOCÊ PERDEU **{abs(points)} CM DE TETA**."
    
    message += f"\nO TAMANHO DA SUA TETA É **{novo_tamanho} CM, PEITUDA METIDA!**"
    return message

def get_ranking(chat_id):
    """Retorna o ranking do chat"""
    result = execute_sql(
        'SELECT username, tamanho_teta FROM player_tetas WHERE chat_id = %s ORDER BY tamanho_teta DESC LIMIT 10',
        (chat_id,),
        fetch=True
    )
    
    if result is None:
        return "❌ Erro ao buscar ranking."
    
    if not result:
        return "Ranking vazio. Use /jogar para começar!"
    
    ranking_text = "**RANKING DO DIA**\n\n"
    for i, (username, tamanho_teta) in enumerate(result, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}º"
        username_display = f"@{username}" if username else "Usuário Anônimo"
        ranking_text += f"{medal} - {username_display}: **{tamanho_teta} CM**\n"
    
    return ranking_text

def get_user_stats(user_id, chat_id):
    """Retorna estatísticas do usuário"""
    result = execute_sql(
        'SELECT username, tamanho_teta, total_plays, last_play FROM player_tetas WHERE user_id = %s AND chat_id = %s',
        (user_id, chat_id),
        fetch=True
    )
    
    if not result:
        return "ℹ️ USE /jogar PARA MEDIR O TAMANHO DESSA SUA TETA"
    
    username, tamanho, total_plays, last_play = result[0]
    last_play_date = last_play.strftime("%d/%m/%Y %H:%M") if last_play else "Nunca"
    status = "HORA DE VER SE GANHA OU PERDE" if is_new_day(last_play) else "JÁ JOGOU HOJE - Volte amanhã!"
    
    return (f"👤 **Estatísticas de @{username}**\n\n"
            f"📊 Tamanho da teta: **{tamanho} CM**\n"
            f"🎯 Total de jogadas: **{total_plays}**\n"
            f"🕒 Última jogada: **{last_play_date}**\n"
            f"📅 Status: **{status}**")

def send_message(chat_id, text):
    """Envia mensagem via Telegram API"""
    try:
        url = URL + "sendMessage"
        params = {
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"❌ Erro ao enviar mensagem: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Erro send_message: {e}")

def process_message(update):
    """Processa uma mensagem recebida"""
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user_id = message["from"]["id"]
    username = message["from"].get("username", f"user_{user_id}")
    
    logger.info(f"📨 Mensagem de @{username}: {text}")
    
    # Verifica se é grupo
    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return
    
    try:
        if text.startswith("/jogar"):
            response = handle_daily_play(user_id, username, chat_id)
            send_message(chat_id, response)
            
        elif text.startswith("/ranking"):
            response = get_ranking(chat_id)
            send_message(chat_id, response)
            
        elif text.startswith("/meupainel"):
            response = get_user_stats(user_id, chat_id)
            send_message(chat_id, response)
            
        elif text.startswith("/start") or text.startswith("/ajuda"):
            send_message(chat_id,
                "🎮 **BOT DE RANKING DIÁRIO** 🎮\n\n"
                "/jogar - Jogar uma vez por dia\n"
                "/ranking - Ver o ranking\n"
                "/meupainel - Ver suas estatísticas"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro process_message: {e}")
        send_message(chat_id, "❌ Erro interno. Tente novamente.")

def get_updates(offset=None):
    """Busca updates do Telegram"""
    try:
        url = URL + "getUpdates"
        params = {"timeout": 100, "offset": offset}
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Erro get_updates: {e}")
        return {"ok": False, "result": []}

def main():
    """Função principal"""
    logger.info("🚀 Iniciando bot...")
    
    if not init_db():
        logger.error("❌ Falha ao inicializar banco de dados")
        return
    
    logger.info("✅ Bot iniciado com sucesso!")
    
    last_update_id = None
    error_count = 0
    
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
                logger.warning(f"⚠️ Resposta não-OK da API (erro {error_count}/5)")
                
        except Exception as e:
            error_count += 1
            logger.error(f"❌ Erro no loop principal: {e}")
        
        # Pausa em caso de muitos erros
        if error_count >= 5:
            logger.error("⏸️ Muitos erros, aguardando 30 segundos...")
            time.sleep(30)
            error_count = 0
        
        time.sleep(1)

if __name__ == "__main__":
    main()