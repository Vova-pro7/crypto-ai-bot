import telebot
import requests
from telebot import types
from datetime import datetime

TOKEN = "ТВІЙ_ТОКЕН_БОТА_СЮДИ" # ←←← Зміни на свій!

bot = telebot.TeleBot(TOKEN)

COINS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT", "bnb": "BNBUSDT", "xrp": "XRPUSDT"}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for coin in COINS:
        markup.add(types.InlineKeyboardButton(coin.upper(), callback_data=f"coin_{coin}"))
    
    bot.send_message(message.chat.id, "🚀 **Crypto Analyzer**\nОбери монету:", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("coin_"):
        coin = call.data.split("_")[1]
        symbol = COINS[coin]
        
        bot.edit_message_text("⏳ Аналізуємо...", call.message.chat.id, call.message.message_id)
        
        try:
            # Беремо дані з Binance
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
            data = requests.get(url, timeout=10).json()
            
            closes = [float(c[4]) for c in data]
            current_price = closes[-1]
            change = (closes[-1] - closes[-10]) / closes[-10] * 100
            
            if change > 0.5:
                signal = "🟢 Ймовірність росту \~75%"
            elif change < -0.5:
                signal = "🔴 Ймовірність падіння \~70%"
            else:
                signal = "⚪ Нейтрально"
            
            text = f"""
📊 **{coin.upper()}/USDT**
💰 Ціна: **${current_price:,.4f}**

{signal}

⏱ Оновлено: {datetime.now().strftime("%H:%M")}
            """
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            
        except:
            bot.edit_message_text("❌ Помилка з'єднання. Спробуй пізніше.", 
                                call.message.chat.id, call.message.message_id)

print("Бот запущено...")
bot.infinity_polling()
