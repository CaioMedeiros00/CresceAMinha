import requests
import time
import json
import random
from datetime import datetime, timedelta
import os

# Configurações
TOKEN = "8299509958:AAGgE1B_luQeSUgzWYzpsLz-LQlPshMuJdI"
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
    # 70% chance de ganhar, 30% chance de perder
    if random.random() < 0.7:
        return random.randint(1, 10)  # Ganha pontos positivos
    else:
        return random.randint(-5, -1)  # Perde pontos

# Comando /jogar
def handle_daily_play(user_id, username, chat_id):
    data = load_data()
    
    # Inicializar usuário se não existir
    if str(user_id) not in data:
        data[str(user_id)] = {
            "username": username,
            "score": 0,
            "last_play": None,
            "total_plays": 0
        }
    
    user_data = data[str(user_id)]
    
    # Verificar se já jogou hoje
    if not is_new_day(user_data["last_play"]):
        return "❌ Você já jogou hoje! Volte amanhã para tentar novamente."
    
    # Gerar resultado
    points = generate_daily_result()
    user_data["score"] += points
    user_data["last_play"] = datetime.now().isoformat()
    user_data["total_plays"] += 1
    
    save_data(data)
    
    # Mensagem de resultado
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
    
    # Ordenar por score
    sorted_users = sorted(data.items(), key=lambda x: x[1]["score"], reverse=True)
    
    ranking_text = "🏆 **RANKING DO DIA** 🏆\n\n"
    
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):  # Top 10
        medal = ""
        if i == 1: medal = "🥇 "
        elif i == 2: medal = "🥈 "
        elif i == 3: medal = "🥉 "
        
        username = user_data.get("username", "Usuário")
        score = user_data["score"]
        ranking_text += f"{medal}{i}º - @{username}: **{score} pontos**\n"
    
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
    
    if last_play:
        last_play_date = datetime.fromisoformat(last_play).strftime("%d/%m/%Y %H:%M")
    else:
        last_play_date = "Nunca"
    
    message = f"👤 **Painel de @{username}**\n\n"
    message += f"📊 Pontuação: **{score} pontos**\n"
    message += f"🎯 Total de jogadas: **{total_plays}**\n"
    message += f"🕒 Última jogada: **{last_play_date}**\n"
    
    # Verificar se pode jogar hoje
    can_play = is_new_day(last_play)
    status = "✅ Pode jogar hoje!" if can_play else "❌ Já jogou hoje"
    message += f"📅 Status: **{status}**"
    
    return message

# Processar mensagens
def process_message(update):
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]
    username = message["from"].get("username", f"user_{user_id}")
    
    # Só funciona em grupos/supergrupos
    if message["chat"]["type"] not in ["group", "supergroup"]:
        send_message(chat_id, "⚠️ Este bot funciona apenas em grupos!")
        return
    
    if text.startswith("/jogar"):
        response = handle_daily_play(user_id, username, chat_id)
        send_message(chat_id, response)
    
    elif text.startswith("/ranking"):
        response = get_ranking(chat_id)
        send_message(chat_id, response)
    
    elif text.startswith("/meupainel"):
        response = get_user_stats(user_id)
        send_message(chat_id, response)
    
    elif text.startswith("/start") or text.startswith("/ajuda"):
        help_text = """🎮 **BOT DE RANKING DIÁRIO** 🎮

Comandos disponíveis:
/jogar - Jogue uma vez por dia para ganhar pontos
/ranking - Ver o ranking dos melhores jogadores
/meupainel - Ver suas estatísticas pessoais

📝 **Como funciona:**
- Use /jogar uma vez por dia
- Ganhe ou perda pontos aleatoriamente
- Compita com seus amigos no ranking!"""
        send_message(chat_id, help_text)

# Funções do Telegram
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
    params = {
        "chat_id": chat_id, 
        "text": text,
        "parse_mode": "Markdown"
    }
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