import telebot
import requests
import json
import base64
import time
import threading

# --- CREDENTIALS ---
BOT_TOKEN = '8266125587:AAFjQ13rodEhwJW-Gre8nyNVue02xjo4TPg'
GITHUB_TOKEN = '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' 
REPO = 'gol131111-ctrl/electrum-' # Проверь наличие слэша в конце в конфиге Гитхаба
DB_FILE = 'db.json'

bot = telebot.TeleBot(BOT_TOKEN)

def get_db():
    try:
        # ИСПРАВЛЕНО: Добавлен слэш в URL
        url = f"https://api.github.com/repos/{REPO}/contents/{DB_FILE}"
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        res = requests.get(url, headers=headers).json()
        if 'content' not in res: return None, None
        content = base64.b64decode(res['content']).decode('utf-8')
        return json.loads(content), res['sha']
    except Exception as e:
        print(f"❌ Ошибка чтения: {e}")
        return None, None

def save_db(data, sha):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{DB_FILE}"
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        content_encoded = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        payload = {"message": "System Sync", "content": content_encoded, "sha": sha}
        requests.put(url, headers=headers, json=payload)
    except Exception as e: print(f"❌ Ошибка записи: {e}")

# --- МОЩНАЯ РАССЫЛКА ---
def check_broadcast():
    while True:
        try:
            db, sha = get_db()
            # Проверяем поле из админки (broadcast -> txt)
            if db and db.get('broadcast') and db['broadcast'].get('txt'):
                msg = db['broadcast']['txt']
                users = db.get('users', [])
                print(f"📢 Рассылка запущена...")
                
                for u in users:
                    uid = u['id'] if isinstance(u, dict) else u # Защита от разного формата ID
                    try:
                        bot.send_message(uid, f"🔔 <b>ОПОВЕЩЕНИЕ</b>\n\n{msg}", parse_mode='HTML')
                        time.sleep(0.05)
                    except: continue 
                
                # Чистим сообщение, чтобы не спамило по кругу
                db['broadcast']['txt'] = ""
                save_db(db, sha)
                print("✅ Рассылка завершена")
        except: pass
        time.sleep(30)

threading.Thread(target=check_broadcast, daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    db, sha = get_db()
    
    # Авто-регистрация (совместимая с форматом админки)
    if db:
        if not any(u['id'] == uid for u in db['users'] if isinstance(u, dict)):
            db['users'].append({"id": uid, "name": message.from_user.first_name, "balance": 0})
            save_db(db, sha)

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    if db and 'categories' in db:
        btns = [telebot.types.InlineKeyboardButton(c, callback_data=f"cat_{c}") for c in db['categories']]
        markup.add(*btns)
    
    bot.send_message(uid, "💎 <b>ELECTRUM OS ONLINE</b>\nВыберите раздел:", parse_mode='HTML', reply_markup=markup)

# ... остальной код (show_products, prod_details) оставляем, он четкий ...

print("🚀 СИСТЕМА ПОЛНОСТЬЮ ГОТОВА")
bot.polling(none_stop=True)
