import os
import telebot
from telebot import types
import requests
from threading import Thread
from flask import Flask

TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не встановлена!")

bot = telebot.TeleBot(TOKEN)
app = Flask('')

MOCOINS = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT', 'BNB': 'BNBUSDT', 'XRP': 'XRPUSDT'}
TIMEFRAMES = {'1m': '1', '5m': '5', '15m': '15', '30m': '30', '1h': '60'}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_bybit_analysis(coin_pair, interval='1'):
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {"category": "spot", "symbol": coin_pair, "interval": interval, "limit": 1}
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("retCode") == 0 and data.get("result", {}).get("list"):
            kline = data["result"]["list"][0]
            
            open_price = float(kline[1])
            close_price = float(kline[4])
            high_price = float(kline[2])
            low_price = float(kline[3])
            volume = float(kline[7])
            
            change = ((close_price - open_price) / open_price) * 100 if open_price != 0 else 0
            
            return {
                'success': True,
                'open': open_price,
                'close': close_price,
                'high': high_price,
                'low': low_price,
                'volume': volume,
                'change': change
            }
        else:
            return {'success': False, 'error': 'Немає даних'}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': '⏱️ Timeout'}
    except Exception as e:
        return {'success': False, 'error': f'❌ {str(e)[:40]}'}

def format_analysis(coin, analysis, timeframe='1m'):
    if not analysis.get('success'):
        return f"❌ {coin} - {analysis.get('error')}"
    
    emoji = "🟢" if analysis['change'] > 0 else "🔴"
    
    return f"""
╔══════════════════════════════════╗
║  📊 {coin} ({timeframe})
╚══════════════════════════════════╝

💰 Open:  ${analysis['open']:,.2f}
💰 Close: ${analysis['close']:,.2f}
📈 High:  ${analysis['high']:,.2f}
📉 Low:   ${analysis['low']:,.2f}
📦 Vol:   ${analysis['volume']:,.0f}

{emoji} {analysis['change']:+.2f}%

{"🚀 BUY!" if analysis['change'] > 2 else "📉 SELL!" if analysis['change'] < -2 else "➡️ WAIT"}
"""

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    for coin in MOCOINS.keys():
        markup.add(types.InlineKeyboardButton(f"📊 {coin}", callback_data=f"coin_{coin}"))
    
    bot.send_message(message.chat.id, "🚀 Привіт! Виберіть монету:", reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, "🔧 Натискай на кнопки для аналізу! ✨")

@bot.callback_query_handler(func=lambda call: call.data.startswith('coin_'))
def coin_selected(call):
    coin = call.data.split('_')[1]
    symbol = MOCOINS.get(coin)
    
    if not symbol:
        return
    
    bot.edit_message_text(f"⏳ Завантажуємо {coin}...", call.message.chat.id, call.message.message_id)
    
    analysis = get_bybit_analysis(symbol)
    text = format_analysis(coin, analysis)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Оновити", callback_data=f"refresh_{coin}"))
    markup.add(types.InlineKeyboardButton("← Назад", callback_data="back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('refresh_'))
def refresh_coin(call):
    coin = call.data.split('_')[1]
    symbol = MOCOINS.get(coin)
    analysis = get_bybit_analysis(symbol)
    text = format_analysis(coin, analysis)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Оновити", callback_data=f"refresh_{coin}"))
    markup.add(types.InlineKeyboardButton("← Назад", callback_data="back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'back')
def go_back(call):
    markup = types.InlineKeyboardMarkup()
    for coin in MOCOINS.keys():
        markup.add(types.InlineKeyboardButton(f"📊 {coin}", callback_data=f"coin_{coin}"))
    
    bot.edit_message_text("Виберіть монету:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@app.route('/')
def home():
    return "Bot is alive 🤖"

if __name__ == '__main__':
    print("🚀 Бот запустився!")
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))), daemon=True).start()
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("⛔ Бот зупинений")
