import telebot
import requests
import json
import base64
from telebot import types

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = '8266125587:AAFjQ13rodEhwJW-Gre8nyNVue02xjo4TPg'
GITHUB_TOKEN = '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'
REPO = 'gol131111-ctrl/electrum-'
DB_PATH = 'db.json'

bot = telebot.TeleBot(BOT_TOKEN)

def get_db():
    url = f"https://api.github.com/repos/{REPO}/contents/{DB_PATH}"
    res = requests.get(url, headers={'Authorization': f'token {GITHUB_TOKEN}', 'Cache-Control': 'no-cache'})
    data = res.json()
    content = base64.b64decode(data['content']).decode('utf-8')
    return json.loads(content), data['sha']

def update_db(new_db, sha):
    content = base64.b64encode(json.dumps(new_db, indent=2, ensure_ascii=False).encode('utf-8')).decode('utf-8')
    url = f"https://api.github.com/repos/{REPO}/contents/{DB_PATH}"
    requests.put(url, headers={'Authorization': f'token {GITHUB_TOKEN}'}, 
                 json={"message": "Bot Update", "content": content, "sha": sha})

@bot.message_handler(commands=['start'])
def start(message):
    db, _ = get_db()
    
    # Сохраняем пользователя в базу (CRM)
    user_exists = any(u['id'] == message.from_user.id for u in db.get('users', []))
    if not user_exists:
        db.setdefault('users', []).append({'id': message.from_user.id, 'name': message.from_user.first_name})
        # Здесь можно добавить вызов update_db, если нужно сохранять юзеров сразу

    markup = types.InlineKeyboardMarkup(row_width=2)
    cats = db.get('categories', ["Общее"])
    buttons = [types.InlineKeyboardButton(text=f"💎 {c}", callback_data=f"cat_{c}") for c in cats]
    markup.add(*buttons)
    
    welcome = db['settings'].get('welcome_text', 'Добро пожаловать в ELECTRUM!')
    bot.send_message(message.chat.id, f"<b>{welcome}</b>\n\nВыберите раздел каталога:", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def show_cat(call):
    cat_name = call.data.split('_')[1]
    db, _ = get_db()
    products = [p for p in db['products'] if p.get('cat') == cat_name]
    
    if not products:
        bot.answer_callback_query(call.id, "В этом разделе пока нет товаров")
        return

    for p in products:
        text = f"<b>{p['name']}</b>\n\n{p['desc']}\n\n💰 Цена: {p['price']} ₽"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛍 Купить", callback_data=f"buy_{p['id']}"))
        
        if p.get('img') and p['img'].startswith('http'):
            bot.send_photo(call.message.chat.id, p['img'], caption=text, parse_mode='HTML', reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    # Тут можно добавить логику уведомления менеджера
    bot.send_message(call.message.chat.id, "✅ <b>Заказ принят!</b>\nМенеджер свяжется с вами в ближайшее время.", parse_mode='HTML')

print("ELECTRUM SYSTEM ONLINE ❤️‍🔥")
bot.polling(none_stop=True)
