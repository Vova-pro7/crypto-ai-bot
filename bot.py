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

# Пари
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

def calculate_ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
            
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100.0
        
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * 13 + gains[i]) / 14
        avg_loss = (avg_loss * 13 + losses[i]) / 14
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze_market(coin, interval):
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={coin}&tsym=USDT&limit=150&aggregate={interval}"
        res = requests.get(url, timeout=10).json()
        
        if 'Data' in res and 'Data' in res['Data'] and len(res['Data']['Data']) > 0:
            candles = res['Data']['Data']
            
            closes = [float(c['close']) for c in candles]
            highs = [float(c['high']) for c in candles]
            lows = [float(c['low']) for c in candles]
            
            if len(closes) < 30:
                return "⚠️ Мало даних для аналізу ринку. Спробуйте пізніше."
                
            close_price = closes[-1]
            rsi_val = calculate_rsi(closes, 14)
            
            # Алігатор (вручну через зміщення та EMA)
            jaw = calculate_ema(closes[:-8], 13) if len(closes) > 8 else closes[-1]
            teeth = calculate_ema(closes[:-5], 8) if len(closes) > 5 else closes[-1]
            lips = calculate_ema(closes[:-3], 5) if len(closes) > 3 else closes[-1]
            
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
                
            text = (
                f"📊 **Аналіз: {coin}USDT**\n"
                f"⏱ **Таймфрейм:** {interval}м\n"
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
        print(f"Помилка: {e}")
        
    return "⚠️ Помилка обробки ринку. Натисніть кнопку таймфрейму ще раз!"

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
