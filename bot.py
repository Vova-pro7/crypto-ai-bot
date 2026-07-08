import telebot
from telebot import types
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time

# ================== НАЛАШТУВАННЯ ==================
TOKEN = "ТВІЙ_ТОКЕН_БОТА" # Заміни на токен від @BotFather

bot = telebot.TeleBot(TOKEN)

# Коіни
COINS = {
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "sol": "SOLUSDT",
    "bnb": "BNBUSDT",
    "xrp": "XRPUSDT"
}

# Таймфрейми
TIMEFRAMES = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60"
}

# ================== ФУНКЦІЇ АНАЛІЗУ ==================
def get_klines(symbol, interval, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}m&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                         'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 
                                         'taker_buy_quote', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        return df
    except Exception as e:
        print(f"Помилка Binance: {e}")
        return None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def simple_signal(df):
    if len(df) < 50:
        return "❓ Недостатньо даних", 50.0
    
    close = df['close']
    rsi = calculate_rsi(close).iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]
    current_price = close.iloc[-1]
    
    # Логіка сигналу
    score = 0
    if current_price > ma20 and ma20 > ma50:
        score += 30 # Булліш тренд
    if rsi < 30:
        score += 25 # Перепроданість
    elif rsi > 70:
        score -= 25 # Перекупленість
    
    # Додаткові фактори
    if close.iloc[-1] > close.iloc[-5]:
        score += 15
    if close.iloc[-1] > close.iloc[-10]:
        score += 10
    
    prob_up = min(85, max(15, 50 + score))
    prob_down = 100 - prob_up
    
    if prob_up > 65:
        return f"🟢 **СИГНАЛ НА ЗРОСТАННЯ**", round(prob_up, 1)
    elif prob_down > 65:
        return f"🔴 **СИГНАЛ НА ПАДІННЯ**", round(prob_down, 1)
    else:
        return "⚪ **НЕЙТРАЛЬНО**", round(prob_up, 1)

# ================== ОБРОБНИКИ ==================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, sym in COINS.items():
        markup.add(types.InlineKeyboardButton(name.upper(), callback_data=f"coin_{name}"))
    
    text = "🚀 **Crypto AI Analyzer**\n\nОберіть монету:"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("coin_"))
def coin_selected(call):
    coin = call.data.split("_")[1]
    symbol = COINS[coin]
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    for tf_name, _ in TIMEFRAMES.items():
        markup.add(types.InlineKeyboardButton(tf_name, callback_data=f"tf_{coin}_{tf_name}"))
    
    bot.edit_message_text(
        f"📊 **{coin.upper()}**\nОберіть таймфрейм:", 
        call.message.chat.id, 
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("tf_"))
def analyze(call):
    _, coin, tf = call.data.split("_")
    symbol = COINS[coin]
    interval = TIMEFRAMES[tf]
    
    bot.edit_message_text(
        f"🔄 Аналізуємо {coin.upper()} на {tf}...\n\n⏳ Завантажуємо дані...",
        call.message.chat.id,
        call.message.message_id
    )
    
    df = get_klines(symbol, interval)
    if df is None:
        bot.edit_message_text("❌ Помилка підключення до Binance", call.message.chat.id, call.message.message_id)
        return
    
    signal, prob = simple_signal(df)
    price = df['close'].iloc[-1]
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    text = f"""
📈 **{coin.upper()}/USDT** — {tf}
💰 Ціна: **${price:,.4f}**

{signal}
**Ймовірність:** `{prob}%`

⏱ Оновлено: {timestamp}
    """
    
    # Кнопки для швидкого повтору
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Оновити", callback_data=f"tf_{coin}_{tf}"))
    markup.add(types.InlineKeyboardButton("◀️ Інші таймфрейми", callback_data=f"coin_{coin}"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         parse_mode='Markdown', reply_markup=markup)

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    print("🤖 Crypto AI Bot запущено...")
    bot.infinity_polling()
