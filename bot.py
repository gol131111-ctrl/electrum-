import telebot
import requests
import json
import base64
import time
import threading

# --- НАСТРОЙКИ (ТОКЕН УЖЕ ВНУТРИ) ---
BOT_TOKEN = '8266125587:AAFjQ13rodEhwJW-Gre8nyNVue02xjo4TPg'
GITHUB_TOKEN = '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' 
REPO = 'gol131111-ctrl/electrum-'
DB_FILE = 'db.json'

bot = telebot.TeleBot(BOT_TOKEN)

# --- ФУНКЦИИ РАБОТЫ С БАЗОЙ (GITHUB) ---
def get_db():
    try:
        url = f"https://api.github.com/repos/{REPO}contents/{DB_FILE}"
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        res = requests.get(url, headers=headers).json()
        if 'content' not in res:
            return None, None
        content = base64.b64decode(res['content']).decode('utf-8')
        return json.loads(content), res['sha']
    except Exception as e:
        print(f"Ошибка чтения БД: {e}")
        return None, None

def save_db(data, sha):
    try:
        url = f"https://api.github.com/repos/{REPO}contents/{DB_FILE}"
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        content_encoded = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        payload = {
            "message": "Bot update",
            "content": content_encoded,
            "sha": sha
        }
        requests.put(url, headers=headers, json=payload)
    except Exception as e:
        print(f"Ошибка записи БД: {e}")

# --- ФОНОВАЯ ПРОВЕРКА РАССЫЛКИ (РАЗ В МИНУТУ) ---
def check_broadcast():
    while True:
        try:
            db, sha = get_db()
            if db and db.get('broadcast_msg'):
                msg = db['broadcast_msg']
                users = db.get('users', [])
                print(f"📢 Запуск рассылки: {msg}")
                
                count = 0
                for user_id in users:
                    try:
                        bot.send_message(user_id, f"⚡️ <b>НОВОСТИ ELECTRUM</b> ⚡️\n\n{msg}", parse_mode='HTML')
                        count += 1
                        time.sleep(0.1) # Защита от спам-фильтра Telegram
                    except:
                        continue 
                
                # Очищаем флаг рассылки в базе
                db['broadcast_msg'] = ""
                save_db(db, sha)
                print(f"✅ Рассылка завершена. Получили: {count} чел.")
        except Exception as e:
            print(f"Ошибка рассылки: {e}")
        time.sleep(60)

threading.Thread(target=check_broadcast, daemon=True).start()

# --- ОБРАБОТКА КОМАНД ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # Регистрация нового пользователя
    def reg():
        db, sha = get_db()
        if db:
            if 'users' not in db: db['users'] = []
            if user_id not in db['users']:
                db['users'].append(user_id)
                save_db(db, sha)
    threading.Thread(target=reg).start()

    # Главное меню
    db, _ = get_db()
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    if db and 'categories' in db:
        btns = [telebot.types.InlineKeyboardButton(f"📁 {c}", callback_data=f"cat_{c}") for c in db['categories']]
        markup.add(*btns)
    
    bot.send_message(user_id, "👋 <b>Добро пожаловать в ELECTRUM!</b>\n\nВыберите категорию товара:", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def show_products(call):
    cat_name = call.data.split('_')[1]
    db, _ = get_db()
    markup = telebot.types.InlineKeyboardMarkup()
    found = False
    if db:
        for p in db['products']:
            if p['cat'] == cat_name:
                found = True
                markup.add(telebot.types.InlineKeyboardButton(f"{p['name']} — {p['price']}₽", callback_data=f"prod_{p['id']}"))
    
    markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="back_home"))
    bot.edit_message_text(f"📂 Категория: <b>{cat_name}</b>", call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('prod_'))
def show_details(call):
    p_id = int(call.data.split('_')[1])
    db, _ = get_db()
    product = next((x for x in db['products'] if x['id'] == p_id), None)
    if product:
        txt = f"<b>{product['name']}</b>\n\n{product['desc']}\n\n💰 Цена: <b>{product['price']}₽</b>"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("💳 Купить", callback_data="buy"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data=f"cat_{product['cat']}"))
        if product.get('img'):
            bot.send_photo(call.message.chat.id, product['img'], caption=txt, parse_mode='HTML', reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, txt, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back(call):
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy(call):
    bot.answer_callback_query(call.id, "Оплата временно через администратора!", show_alert=True)

print("ELECTRUM SYSTEM ONLINE ❤️‍🔥")
bot.polling(none_stop=True)
