import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")

async def fetch_candles(symbol: str, interval: str, limit: int = 50) -> list:
    """Завантажує історичні свічки з Binance для аналізу"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.error(f"Error fetching candles for {interval}: {e}")
    return []

def calculate_rsi(prices, period=14):
    """Рахує індикатор RSI для визначення перекупленості/перепроданості"""
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            up_chg = delta
            down_chg = 0.
        else:
            up_chg = 0.
            down_chg = -delta
        up = (up * (period - 1) + up_chg) / period
        down = (down * (period - 1) + down_chg) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi[-1]

def analyze_market(candles) -> dict:
    """Математичний аналіз тренду, RSI та розрахунок % ймовірності руху"""
    if not candles or len(candles) < 25:
        return {"dir": "ФЛЕТ 🟡", "prob": 50, "rsi": 50, "price": 0}
    
    closes = np.array([float(c[4]) for c in candles])
    current_price = closes[-1]
    
    ma7 = np.mean(closes[-7:])
    ma25 = np.mean(closes[-25:])
    rsi = calculate_rsi(closes)
    
    bullish_score = 0
    total_score = 4
    
    if current_price > ma7: bullish_score += 1
    if ma7 > ma25: bullish_score += 1
    if rsi < 40: bullish_score += 1.5
    if rsi > 70: bullish_score -= 1.5
    if closes[-1] > closes[-2]: bullish_score += 0.5
    
    prob_bullish = (bullish_score / total_score) * 100
    prob_bullish = max(15, min(95, prob_bullish))
    
    if prob_bullish > 55:
        direction = "ВГОРУ 📈"
        probability = prob_bullish
    elif prob_bullish < 45:
        direction = "ВНИЗ 📉"
        probability = 100 - prob_bullish
    else:
        direction = "ФЛЕТ 🟡"
        probability = 50
        
    return {
        "price": current_price,
        "dir": direction,
        "prob": round(probability, 1),
        "rsi": round(rsi, 1)
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("₿ Аналіз BTC", callback_data="tech_BTC"), 
         InlineKeyboardButton("♦ Аналіз ETH", callback_data="tech_ETH")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 **Crypto AI-Trading Bot**\n\nОберіть монету для проведення повного аналізу по всім таймфреймам (1m, 5m, 15m, 30m, 1h):", 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("tech_"):
        symbol = query.data.replace("tech_", "")
        
        await query.edit_message_text(text=f"🔄 Сканую всі таймфрейми для {symbol}... Рахую індикатори...")
        
        # Завантажуємо всі 5 таймфреймів одночасно
        candles_1m = await fetch_candles(symbol, "1m", 40)
        candles_5m = await fetch_candles(symbol, "5m", 40)
        candles_15m = await fetch_candles(symbol, "15m", 40)
        candles_30m = await fetch_candles(symbol, "30m", 40)
        candles_1h = await fetch_candles(symbol, "1h", 40)
        
        if not candles_1m or not candles_5m or not candles_15m or not candles_30m or not candles_1h:
            await query.edit_message_text(text="❌ Помилка: Не вдалося отримати ринкові свічки з API Binance.")
            return
            
        an_1m = analyze_market(candles_1m)
        an_5m = analyze_market(candles_5m)
        an_15m = analyze_market(candles_15m)
        an_30m = analyze_market(candles_30m)
        an_1h = analyze_market(candles_1h)
        
        # Формуємо професійний звіт для трейдера
        msg = (
            f"🎯 **СИГНАЛ: {symbol}/USDT**\n"
            f"💵 Поточна ціна: `${an_1m['price']:,.2f}`\n\n"
            
            f"⏳ **ТФ: 1 ХВИЛИНА (Scalp)**\n"
            f" Напрямок: **{an_1m['dir']}** | Верогідність: `{an_1m['prob']}%` | RSI: `{an_1m['rsi']}`\n\n"
            
            f"⏳ **ТФ: 5 ХВИЛИН (Scalp)**\n"
            f" Напрямок: **{an_5m['dir']}** | Верогідність: `{an_5m['prob']}%` | RSI: `{an_5m['rsi']}`\n\n"
            
            f"⏳ **ТФ: 15 ХВИЛИН (Intraday)**\n"
            f" Напрямок: **{an_15m['dir']}** | Верогідність: `{an_15m['prob']}%` | RSI: `{an_15m['rsi']}`\n\n"
            
            f"⏳ **ТФ: 30 ХВИЛИН (Intraday)**\n"
            f" Напрямок: **{an_30m['dir']}** | Верогідність: `{an_30m['prob']}%` | RSI: `{an_30m['rsi']}`\n\n"
            
            f"⏳ **ТФ: 1 ГОДИНА (Swing)**\n"
            f" Напрямок: **{an_1h['dir']}** | Верогідність: `{an_1h['prob']}%` | RSI: `{an_1h['rsi']}`\n\n"
            
            f"⚡ _Математичний розрахунок проведено за моделями MA7/MA25 + RSI14._"
        )
        
        await query.edit_message_text(text=msg, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.run_polling()

if __name__ == "__main__":
    main()

