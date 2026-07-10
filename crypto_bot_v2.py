import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")

async def get_price(symbol: str) -> dict:
    """Отримує ціну через відкрите API, яке не блокує хостинги"""
    try:
        async with aiohttp.ClientSession() as session:
            if symbol == "BTC":
                # Надійне API блокчейну Біткоїна
                url = "https://mempool.space/api/v1/prices"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'price': float(data.get('USD', 0)),
                            'change24h': 0.0  # Спрощене API без відсотка змін
                        }
            else:
                # Надійне альтернативне API для ETH та інших монет
                url = f"https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        eth_data = data.get('ethereum', {})
                        return {
                            'price': float(eth_data.get('usd', 0)),
                            'change24h': float(eth_data.get('usd_24h_change', 0))
                        }
    except Exception as e:
        logger.error(f"Error fetching price: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("₿ Bitcoin", callback_data="price_BTC"), InlineKeyboardButton("♦ Ethereum", callback_data="price_ETH")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 <b>Crypto Bot</b>\n\nНатисни на крипто!", reply_markup=reply_markup, parse_mode="HTML")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("price_"):
        symbol = query.data.replace("price_", "")
        data = await get_price(symbol)

        if data:
            price = data['price']
            change = data['change24h']
            if symbol == "BTC":
                message = f"📊 <b>{symbol}</b>\n\n💵 Ціна: <code>${price:,.2f}</code>"
            else:
                message = f"📊 <b>{symbol}</b>\n\n💵 Ціна: <code>${price:,.2f}</code>\n📈 24h: <code>{change:+.2f}%</code>"
            await query.edit_message_text(text=message, parse_mode="HTML")
        else:
            await query.edit_message_text(text="❌ Помилка: Сервер не зміг достукатися до мережі.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.run_polling()

if __name__ == "__main__":
    main()

