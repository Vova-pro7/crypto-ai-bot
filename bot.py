import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import requests

# Ініціалізація бота
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

MOCOINS = {'BTC': 'BTC', 'ETH': 'ETH', 'SOL': 'SOL', 'BNB': 'BNB', 'XRP': 'XRP'}
TIMEFRAMES = {'1м': '1', '5м': '5', '15м': '15', '30м': '30'}

def analyze_market(coin, interval):
    try:
        # Беремо готові дані 24-годинної зміни ринку
        url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={coin}&tsyms=USDT"
        res = requests.get(url, timeout=10).json()
        
        if 'DISPLAY' in res and coin in res['DISPLAY'] and 'USDT' in res['DISPLAY'][coin]:
            data = res['DISPLAY'][coin]['USDT']
            raw_data = res['RAW'][coin]['USDT']
            
            price = data['PRICE']
            change_pct = raw_data.get('CHANGEPCT24HOUR', 0)
            high = data['HIGH24HOUR']
            low = data['LOW24HOUR']
            
            # Логіка сигналу на основі добового тренду
            if change_pct > 1.5:
                direction = "ВВЕРХ 🟢 (BUY)"
                score = 85
            elif change_pct < -1.5:
                direction = "ВНИЗ 🔴 (SELL)"
                score = 85
            elif change_pct > 0:
                direction = "ФЛЕТ / СЛАБКИЙ ЛОНГ ↕️"
                score = 60
            else:
                direction = "ФЛЕТ / СЛАБКИЙ ШОРТ ↕️"
                score = 60
                
            text = (
                f"📊 **Аналіз: {coin}/USDT**\n"
                f"⏱ **Таймфрейм:** {interval}\n"
                f"💰 **Поточна ціна:** {price}\n"
                f"-------------------------\n"
                f"📈 **Напрямок:** {direction}\n"
                f"⚡ **Сила тренду:** {score}%\n"
                f"-------------------------\n"
                f"🔮 *Добові дані:*\n"
                f"• Зміна за 24г: {change_pct:.2f}%\n"
                f"• Макс (24г): {high}\n"
                f"• Мін (24г): {low}"
            )
            return text
    except Exception as e:
        print(f"Помилка: {e}")
        
    return "⚠️ Сервер обробки тимчасово перевантажений. Натисніть кнопку ще раз!"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(f"Аналіз {coin}") for coin in MOCOINS.keys()]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Привіт! Виберіть криптовалюту для аналізу:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text.startswith("Аналіз "))
def choose_coin(message):
    coin = message.text.split(" ")[1]
    if coin in MOCOINS:
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(tf, callback_data=f"tf_{coin}_{tf}") for tf in TIMEFRAMES.keys()]
        markup.add(*buttons)
        bot.send_message(message.chat.id, f"Оберіть таймфрейм для {coin}:", reply_markup=markup)

@bot.callback_query_handler(func=func=lambda call: call.data.startswith("tf_"))
def process_analysis(call):
    _, coin, tf = call.data.split("_")
    bot.answer_callback_query(call.id, text="Сканую ринок...")
    result_text = analyze_market(coin, tf)
    bot.send_message(call.message.chat.id, result_text, parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
