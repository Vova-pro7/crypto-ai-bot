import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import requests
import pandas as pd
import pandas_ta as ta

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

# Список монет та таймфреймів
MOCOINS = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'SOL': 'SOLUSDT',
    'BNB': 'BNBUSDT',
    'XRP': 'XRPUSDT'
}

TIMEFRAMES = {
    '1м': '1m',
    '5м': '5m',
    '15м': '15m',
    '30м': '30m'
}

# Функція отримання історичних даних з Binance
def get_candles(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url).json()
        df = pd.DataFrame(response, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'q_volume', 'trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        return df
    except Exception as e:
        print(f"Помилка отримання даних: {e}")
        return None

# Функція аналізу ринку за RSI та Alligator
def analyze_market(symbol, interval):
    df = get_candles(symbol, interval)
    if df is None or df.empty:
        return "Не вдалося отримати дані з ринку."
    
    # Розрахунок RSI (період 14)
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # Розрахунок Алігатора (Щелепа, Зуби, Губи) з базовими зміщеннями
    # Використовуємо медіанну ціну ((high + low) / 2)
    median_price = (df['high'] + df['low']) / 2
    df['jaw'] = ta.smma(median_price, length=13).shift(8)
    df['teeth'] = ta.smma(median_price, length=8).shift(5)
    df['lips'] = ta.smma(median_price, length=5).shift(3)
    
    # Останні значення індикаторів
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    rsi_val = last_row['RSI']
    close_price = last_row['close']
    
    jaw = last_row['jaw']
    teeth = last_row['teeth']
    lips = last_row['lips']
    
    # Логіка сигналів
    score = 0  # Максимум 100% (по 50% на кожен індикатор)
    direction = "ФЛЕТ ↕️"
    
    # 1. Аналіз RSI
    rsi_signal = 0
    if rsi_val < 35:
        rsi_signal = 1  # Перепроданість -> Вверх
    elif rsi_val > 65:
        rsi_signal = -1 # Перекупленість -> Вниз
        
    # 2. Аналіз Алігатора (Переплетення ліній або тренд)
    alligator_signal = 0
    if lips > teeth > jaw and close_price > lips:
        alligator_signal = 1  # Алігатор відкрив пащу вверх
    elif lips < teeth < jaw and close_price < lips:
        alligator_signal = -1 # Алігатор відкрив пащу вниз

    # Фінальний розрахунок напрямку та сили сигналу
    total_signal = rsi_signal + alligator_signal
    
    if total_signal >= 1:
        direction = "ВВЕРХ 🟢 (BUY)"
        # Вираховуємо силу сигналу
        score = 50 if total_signal == 1 else 90
        if rsi_val < 30: score += 10 # Додаткова сила при жорсткій перепроданості
    elif total_signal <= -1:
        direction = "ВНИЗ 🔴 (SELL)"
        score = 50 if total_signal == -1 else 90
        if rsi_val > 70: score += 10
    else:
        direction = "НЕВИЗНАЧЕНО 🟡 (Очікування)"
        score = 30
        
    # Форматування виводу
    text = (
        f"📊 **Аналіз: {symbol}**\n"
        f"⏱ **Таймфрейм:** {interval}\n"
        f"💰 **Поточна ціна:** {close_price:.4f}\n"
        f"-------------------------\n"
        f"📈 **Напрямок:** {direction}\n"
        f"⚡ **Сила сигналу:** {min(score, 100)}%\n"
        f"-------------------------\n"
        f"🔮 *Показники:*\n"
        f"• RSI: {rsi_val:.2f}\n"
        f"• Алігатор: {'Паща відкрита' if alligator_signal != 0 else 'Спить (Флет)'}"
    )
    return text

# Стартова команда
@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(f"Аналіз {coin}") for coin in MOCOINS.keys()]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Привіт! Виберіть криптовалюту для аналізу в реальному часі:", reply_markup=markup)

# Обробка вибору монети
@bot.message_handler(func=lambda msg: msg.text.startswith("Аналіз "))
def choose_coin(message):
    coin = message.text.split(" ")[1]
    if coin in MOCOINS:
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(tf, callback_data=f"tf_{coin}_{raw}") for tf, raw in TIMEFRAMES.items()]
        markup.add(*buttons)
        bot.send_message(message.chat.id, f"Оберіть таймфрейм для {coin}:", reply_markup=markup)

# Обробка інлайн-кнопок з таймфреймами
@bot.callback_query_handler(func=lambda call: call.data.startswith("tf_"))
def process_analysis(call):
    _, coin, tf_raw = call.data.split("_")
    symbol = MOCOINS[coin]
    
    bot.answer_callback_query(call.id, text="Аналізую ринок...")
    
    # Запускаємо аналіз
    result_text = analyze_market(symbol, tf_raw)
    
    bot.send_message(call.message.chat.id, result_text, parse_mode="Markdown")

# Запуск бота
if __name__ == '__main__':
    bot.infinity_polling()
