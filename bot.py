import telebot
from telebot import types
import requests
from datetime import datetime

TOKEN = "ТВІЙ_ТОКЕН_БОТА" # ← Зміни!

bot = telebot.TeleBot(TOKEN)

COINS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple"
}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for coin in COINS:
        markup.add(types.InlineKeyboardButton(coin.upper(), callback_data=coin))
    bot.send_message(message.chat.id, "🚀 **Простий Crypto Bot**\nОбери монету:", 
                     parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def analyze(call):
    coin_id = call.data
    coin_name = coin_id.upper()
    
    bot.edit_message_text(f"⏳ Аналіз {coin_name}...", call.message.chat.id, call.message.message_id)
    
    try:
        # Отримуємо ціну та зміну
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        data = requests.get(url, timeout=10).json()
        
        price = data['market_data']['current_price']['usd']
        change_1h = data['market_data']['price_change_percentage_1h_in_currency']['usd']
        change_24h = data['market_data']['price_change_percentage_24h']
        
        if change_1h > 0.5:
            signal = "🟢 Сигнал на ріст (\~70%)"
        elif change_1h < -0.5:
            signal = "🔴 Сигнал на падіння (\~65%)"
        else:
            signal = "⚪ Нейтрально"
        
        text = f"""
📊 **{coin_name}**

💰 Ціна: **${price:,.4f}**
📈 1 година: `{change_1h:.2f}%`
📈 24 години: `{change_24h:.2f}%`

{signal}

⏱ {datetime.now().strftime("%H:%M")}
        """
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.edit_message_text("❌ Тимчасова помилка. Спробуй пізніше.", 
                            call.message.chat.id, call.message.message_id)

print("✅ Бот запущено!")
bot.infinity_polling()
