import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import requests

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

MOCOINS = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT', 'BNB': 'BNBUSDT', 'XRP': 'XRPUSDT'}
TIMEFRAMES = {'1м': '1', '5м': '5', '15м': '15', '30м': '30'}

def get_bybit_analysis(coin_pair, interval):
    try:
        # Прямий запит свічок з Bybit (працює завжди і без ключів)
        url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={coin_pair}&interval={interval}&limit=50"
        res = requests.get(url, timeout=10).json()
        
        if res.get('retCode') == 0 and 'list' in res.get('result', {}):
            klines = res['result']['list'] # Список свічок від нових до старих
            
            close_price = float(klines[0][4]) # Поточна ціна закриття
            open_24h = float(klines[-1][1]) if len(klines) > 1 else close_price
            
            # Розрахунок зміни ціни в %
            change_pct = ((close_price - open_24h) / open_24h) * 100
            
            # Базовий індикатор на основі останніх свічок (простий тренд)
            last_closes = [float(k[4]) for k in klines[:10]]
            if last_closes[0] > last_closes[-1]:
                direction = "ВВЕРХ 🟢 (BUY)"
                score = 80
            elif last_closes[0] < last_closes[-1]:
                direction = "ВНИЗ 🔴 (SELL)"
                score = 80
            else:
                direction = "ФЛЕТ ↕️"
                score = 50

            text = (
                f"📊 **Аналіз: {coin_pair}**\n"
                f"⏱ **Таймфрейм:** {interval}м\n"
                f"💰 **Поточна ціна:** {close_price:.2f} USDT\n"
                f"-------------------------\n"
                f"📈 **Напрямок:** {direction}\n"
                f"⚡ **Сила сигналу:** {score}%\n"
                f"-------------------------\n"
                f"🔮 *Дані тренду:*\n"
                f"• Зміна за цикл: {change_pct:.2f}%\n"
                f"• Статус: Оновлено з Bybit"
            )
            return text
    except Exception as e:
        print(f"Помилка Bybit: {e}")
    return "⚠️ Помилка зв'язку з Bybit. Натисніть кнопку ще раз через 3 секунди!"

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("tf_"))
def process_analysis(call):
    _, coin, tf_name = call.data.split("_")
    bot.answer_callback_query(call.id, text="Запитую дані з Bybit...")
    
    coin_pair = MOCOINS.get(coin, "BTCUSDT")
    # Переводимо назву кнопки у формат хвилин Bybit
    interval_map = {'1м': '1', '5м': '5', '15м': '15', '30м': '30'}
    bybit_tf = interval_map.get(tf_name, '5')
    
    result_text = get_bybit_analysis(coin_pair, bybit_tf)
    bot.send_message(call.message.chat.id, result_text, parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
