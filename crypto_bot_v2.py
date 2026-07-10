import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")

async def get_price(symbol: str) -> dict:
    """Отримує ціну BTC/ETH"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}USDT"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('result', {}).get('list'):
                        ticker = data['result']['list'][0]
                        return {
                            'price': float(ticker['lastPrice']),
                            'change24h': float(ticker['price24hPcnt']) * 100,
                        }
    except Exception as e:
        logger.error(f"Error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🪙 Bitcoin", callback_data="price_BTC"), InlineKeyboardButton("⟠ Ethereum", callback_data="price_ETH")]
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
            message = f"💰 <b>{symbol}</b>\n━━━\nЦіна: <code>${price:,.2f}</code>\n24h: <code>{change:+.2f}%</code>"
            await query.edit_message_text(text=message, parse_mode="HTML")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    logger.info("🤖 Бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
