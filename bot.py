import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import requests
import pandas as pd

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

# Пари для легкого інфо-сервера
MOCOINS = {
    'BTC': 'BTC',
    'ETH': 'ETH',
    'SOL': 'SOL',
    'BNB': 'BNB',
    'XRP': 'XRP'
}

# Таймфрейми
TIMEFRAMES = {
    '1м': '1',
    '5м': '5',
    '15м': '15',
    '30м': '30'
}

def analyze_market(coin, interval):
    try:
        # Прямий легкий запит хвилинних свічок, який працює всюди
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={coin}&tsym=USDT&limit=100&aggregate={interval}"
        res = requests.get(url, timeout=10).json()
        
        if 'Data' in res and 'Data' in res['Data'] and len(res['Data']['Data']) > 0:
            candles = res['Data']['Data']
            df = pd.DataFrame(candles)
            
            # Нам потрібні high, low, close
            df = df[['high', 'low', 'close']].copy()
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            
            # Розрахунок RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Розрахунок Алігатора
            df['jaw'] = df['close'].ewm(span=13, adjust=False).mean().shift(8)
            df['teeth'] = df['close'].ewm(span=8, adjust=False).mean().shift(5)
            df['lips'] = df['close'].ewm(span=5, adjust=False).mean().shift(3)
            
            last_row = df.iloc[-1]
            rsi_val = last_row['RSI']
            close_price = last_row['close']
            
            jaw = last_row['jaw']
            teeth = last_row['teeth']
            lips = last_row['lips']
            
            if pd.isna(rsi_val):
                rsi_val = 50.0

            score = 50
            direction = "ФЛЕТ ↕️"
            
            rsi_signal = 0
            if rsi_val < 35:
                rsi_signal = 1
            elif rsi_val > 65:
                rsi_signal = -1
                
            alligator_signal = 0
            if lips > teeth > jaw and close_price > lips:
                alligator_signal = 1
            elif lips < teeth < jaw and close_price < lips:
                alligator_signal = -1

            total_signal = rsi_signal + alligator_signal
            
            if total_signal >= 1:
                direction = "ВВЕРХ 🟢 (BUY)"
                score = 75 if total_signal == 1 else 95
                if rsi_val < 30: score += 5
            elif total_signal <= -1:
                direction = "ВНИЗ 🔴 (SELL)"
                score = 75 if total_signal == -1 else 95
                if rsi_val > 70: score += 5
            else:
                direction = "НЕВИЗНАЧЕНО 🟡"
                score = 40
                
            price_str = f"{close_price:.2f}" if close_price > 1 else f"{close_price:.4f}"
            display_tf = f"{interval}м"
                
            text = (
                f"📊 **Аналіз: {coin}USDT**\n"
                f"⏱ **Таймфрейм:** {display_tf}\n"
                f"💰 **Поточна ціна:** {price_str} USDT\n"
                f"-------------------------\n"
                f"📈 **Напрямок:** {direction}\n"
                f"⚡ **Сила сигналу:** {min(score, 100)}%\n"
                f"-------------------------\n"
                f"🔮 *Показники:*\n"
                f"• RSI (14): {rsi_val:.2f}\n"
                f"• Алігатор: {'Паща відкрита' if alligator_signal != 0 else 'Спить'}"
            )
            return text
    except Exception as e:
        print(f"Помилка сервера: {e}")
        
    return "⚠️ Помилка обробки. Будь ласка, натисніть кнопку таймфрейму ще раз!"

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
        buttons = [types.InlineKeyboardButton(tf, callback_data=f"tf_{coin}_{raw}") for tf, raw in TIMEFRAMES.items()]
        markup.add(*buttons)
        bot.send_message(message.chat.id, f"Оберіть таймфрейм для {coin}:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tf_"))
def process_analysis(call):
    _, coin, tf_raw = call.data.split("_")
    bot.answer_callback_query(call.id, text="Сканую ринок...")
    result_text = analyze_market(coin, tf_raw)
    bot.send_message(call.message.chat.id, result_text, parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
