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
# -------------------
# Loop principal
# -------------------
def main():
    logger.info("Iniciando bot...")

    # Inicializa o banco de dados
    if not init_db():
        logger.error("Não foi possível inicializar o banco de dados. Encerrando.")
        return

    logger.info("🤖 Bot de Ranking iniciado com sucesso!")

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
                error_count = 0  # Reset error count on success
            else:
                logger.warning("Resposta não OK do Telegram API")
                error_count += 1

        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            error_count += 1
            time.sleep(5)

        # Se muitos erros consecutivos, espera mais tempo
        if error_count >= max_errors:
            logger.error("Muitos erros consecutivos. Esperando 30 segundos...")
            time.sleep(30)
            error_count = 0

        time.sleep(1)

if __name__ == "__main__":
    main()
                    total_plays INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Tabela player_tetas verificada/criada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar banco (tentativa {attempt + 1}): {e}")
            if conn:
                conn.close()
            time.sleep(2)
    
    logger.error("Falha ao inicializar banco de dados após todas as tentativas")
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
    """Executa uma query SQL com tratamento de erros"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        
        if fetch:
            result = cur.fetchall()
        else:
            result = True  # Retorna True para operações bem-sucedidas sem fetch
            
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
# Comandos do bot - VERSÃO CORRIGIDA
# -------------------
def handle_daily_play(user_id, username, chat_id):
    # Primeiro, busca o usuário
    result = execute_sql(
        'SELECT tamanho_teta, last_play, total_plays FROM player_tetas WHERE user_id = %s AND chat_id = %s',
        (user_id, chat_id),
        fetch=True
    )
    
    if result is None:
        return "❌ Erro no banco de dados. Tente novamente mais tarde."
    
    points = generate_daily_result()
    
    if result:
        # Usuário existe - verifica se já jogou hoje
        tamanho_teta, last_play, total_plays = result[0]
        
        if not is_new_day(last_play):
            return "OH NOJEIRA, TIRA A MÃO DO PEITO! Isso aqui é um grupo de família, volta amanhã!!!!"
        
        novo_tamanho = tamanho_teta + points
        novo_total_plays = total_plays + 1
        
        # Atualiza o registro
        success = execute_sql(
            '''UPDATE player_tetas 
               SET tamanho_teta = %s, last_play = CURRENT_TIMESTAMP, total_plays = %s, 
                   username = %s, updated_at = CURRENT_TIMESTAMP
               WHERE user_id = %s AND chat_id = %s''',
            (novo_tamanho, novo_total_plays, username, user_id, chat_id)
        )
        
    else:
        # Primeira jogada do usuário
        novo_tamanho = points
        novo_total_plays = 1
        
        # Insere novo registro
        success = execute_sql(
            '''INSERT INTO player_tetas (user_id, chat_id, username, tamanho_teta, last_play, total_plays)
               VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)''',
            (user_id, chat_id, username, novo_tamanho, novo_total_plays)
        )
    
    # DEBUG: Log para verificar o que está acontecendo
    logger.info(f"User: {username}, Points: {points}, Success: {success}")
    
    if success is None:
        return "❌ Erro ao salvar os dados. Tente novamente!"
    
    # Mensagem de sucesso
    if points > 0:
        message = f"QUE TETÃO! @{username} VOCÊ GANHOU **+{points} CM DE TETA**!"
    else:
        message = f"Oh dó... @{username} VOCÊ PERDEU **{abs(points)} CM DE TETA**."

    message += f"\nO TAMANHO DA SUA TETA É **{novo_tamanho} CM, PEITUDA METIDA!**"
    return message

def get_ranking(chat_id):
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
        medal = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else ""
        username_display = f"@{username}" if username else "Usuário Anônimo"
        ranking_text += f"{medal}{i}º - {username_display}: **{tamanho_teta} CM DE TETA**\n"
    
    return ranking_text

def get_user_stats(user_id, chat_id):
    result = execute_sql(
        'SELECT username, tamanho_teta, total_plays, last_play FROM player_tetas WHERE user_id = %s AND chat_id = %s',
        (user_id, chat_id),
        fetch=True
    )
    
    if result is None:
        return "❌ Erro ao buscar estatísticas."
    
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

    logger.info(f"Recebido update de @{username} no chat {chat_id}: {text}")

    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return

    try:
        if text.startswith("/jogar"):
            response_text = handle_daily_play(user_id, username, chat_id)
            send_message(chat_id, response_text)
        elif text.startswith("/ranking"):
            send_message(chat_id, get_ranking(chat_id))
        elif text.startswith("/meupainel"):
            send_message(chat_id, get_user_stats(user_id, chat_id))
        elif text.startswith("/start") or text.startswith("/ajuda"):
            send_message(chat_id, 
                "🎮 **BOT DE RANKING DIÁRIO** 🎮\n\n"
                "/jogar - Jogar uma vez por dia\n"
                "/ranking - Ver o ranking\n"
                "/meupainel - Ver suas estatísticas"
            )
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

<<<<<<< HEAD

def main():
    logger.info("Iniciando bot...")
    
    
=======
# -------------------
# Loop principal
# -------------------
def main():
    logger.info("Iniciando bot...")
    
    # Inicializa o banco de dados
>>>>>>> 8a154d144682fbcd5d428671de821f656ff45ab5
    if not init_db():
        logger.error("Não foi possível inicializar o banco de dados. Encerrando.")
        return
    
    logger.info("🤖 Bot de Ranking iniciado com sucesso!")
    
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
<<<<<<< HEAD
                error_count = 0  
=======
                error_count = 0  # Reset error count on success
>>>>>>> 8a154d144682fbcd5d428671de821f656ff45ab5
            else:
                logger.warning("Resposta não OK do Telegram API")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            error_count += 1
            time.sleep(5)
            
<<<<<<< HEAD
        
=======
        # Se muitos erros consecutivos, espera mais tempo
>>>>>>> 8a154d144682fbcd5d428671de821f656ff45ab5
        if error_count >= max_errors:
            logger.error("Muitos erros consecutivos. Esperando 30 segundos...")
            time.sleep(30)
            error_count = 0
            
        time.sleep(1)

if __name__ == "__main__":
    main()