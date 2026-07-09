import json
import requests
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# ========== ВСТАВ СВІЙ ТОКЕН СЮДИ ==========
TELEGRAM_TOKEN = "8997607775:AAEpl1kIxwou1w81BzPMtX2W_clFL8_p2vg"

# ========== КНОПКИ ==========
STEP_BUTTONS = [
    [KeyboardButton("📊 Step 100"), KeyboardButton("📊 Step 200")],
    [KeyboardButton("📊 Step 300"), KeyboardButton("📊 Step 400")],
    [KeyboardButton("📊 Step 500")]
]
TIME_BUTTONS = [
    [KeyboardButton("1 хв"), KeyboardButton("5 хв"), KeyboardButton("15 хв")],
    [KeyboardButton("30 хв"), KeyboardButton("60 хв")]
]

# ========== АЛІГАТОР ==========
def calculate_sma(data, period):
    if len(data) < period:
        return None
    return sum(data[-period:]) / period

def alligator_signal(prices):
    if len(prices) < 20:
        return "Недостатньо даних", 0
    jaw = calculate_sma(prices, 13)
    teeth = calculate_sma(prices, 8)
    lips = calculate_sma(prices, 5)
    if None in (jaw, teeth, lips):
        return "Немає даних", 0
    if jaw < teeth < lips:
        return "ВВЕРХ ⬆️", 72
    elif jaw > teeth > lips:
        return "ВНИЗ ⬇️", 72
    else:
        return "Немає сигналу (флет)", 0

# ========== ОТРИМАННЯ ДАНИХ (HTTP, без WebSocket) ==========
def fetch_ticks_rest(symbol, count=50):
    url = "https://api.deriv.com/v1/ticks"
    params = {
        "symbol": symbol,
        "count": count,
        "app_id": 1089
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "ticks" in data and data["ticks"]:
                return [float(t["quote"]) for t in data["ticks"]]
    except Exception as e:
        print("Помилка:", e)
    return []

# ========== БОТ ==========
async def start(update: Update, context):
    context.user_data['step'] = None
    await update.message.reply_text(
        "🐊 Привіт! Обери індекс:",
        reply_markup=ReplyKeyboardMarkup(STEP_BUTTONS, resize_keyboard=True)
    )

async def handle_message(update: Update, context):
    text = update.message.text
    user_data = context.user_data

    if text.startswith("📊 Step "):
        step = text.replace("📊 Step ", "")
        user_data['step'] = step
        await update.message.reply_text(
            f"✅ Обрано Step {step}. Тепер обери час:",
            reply_markup=ReplyKeyboardMarkup(TIME_BUTTONS, resize_keyboard=True)
        )
        return

    if text.endswith("хв"):
        time_min = text.replace(" хв", "")
        step = user_data.get('step')
        if not step:
            await update.message.reply_text("Спочатку обери індекс!", reply_markup=ReplyKeyboardMarkup(STEP_BUTTONS, resize_keyboard=True))
            return

        symbol = f"STEP_{step}"
        await update.message.reply_text(f"🔍 Аналізую {symbol}...")
        prices = fetch_ticks_rest(symbol, 50)

        if not prices:
            await update.message.reply_text(
                "❌ Дані не отримано. Спробуй ще раз.",
                reply_markup=ReplyKeyboardMarkup(STEP_BUTTONS, resize_keyboard=True)
            )
            return

        signal_text, conf = alligator_signal(prices)
        current = prices[-1]
        reply = (f"📊 **Індекс {step}**\n"
                 f"⏱ Експірація: {time_min} хв\n"
                 f"💰 Ціна: {current:.2f}\n"
                 f"🐊 Сигнал: **{signal_text}**\n")
        if conf:
            reply += f"📈 Ймовірність: {conf}%"

        await update.message.reply_text(reply, parse_mode="Markdown")
        await update.message.reply_text("Обери наступний індекс:", reply_markup=ReplyKeyboardMarkup(STEP_BUTTONS, resize_keyboard=True))
        return

    await update.message.reply_text("Натисни кнопку знизу 😉", reply_markup=ReplyKeyboardMarkup(STEP_BUTTONS, resize_keyboard=True))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🐊 Бот запущено! 🎉")
    app.run_polling()

if __name__ == "__main__":
    main()

