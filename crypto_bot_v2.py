import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from multi_timeframe import MultiTimeframeAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("8834500006:AAEzSOApYmgdKgglWB0Y_9aWkT52nFkuMSY"
, "YOUR_TOKEN")

analyzer = MultiTimeframeAnalyzer()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🪙 Bitcoin", callback_data="price_BTC"), InlineKeyboardButton("⟠ Ethereum", callback_data="price_ETH")],
        [InlineKeyboardButton("📊 Мульти-ТФ (BTC)", callback_data="mtf_BTC"), InlineKeyboardButton("📊 Мульти-ТФ (ETH)", callback_data="mtf_ETH")],
        [InlineKeyboardButton("⚡ Швидкий скан (BTC)", callback_data="scan_BTC"), InlineKeyboardButton("⚡ Швидкий скан (ETH)", callback_data="scan_ETH")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 <b>Crypto Multi-Timeframe Analyzer</b>\n\n✨ <b>Що це робить:</b>\n• Аналізує BTC/ETH на 5 таймфреймах\n• Confidence система = % впевненості\n• RSI, MA, Williams Alligator\n• Знаходить найсильніший сигнал\n\n<b>📱 Таймфрейми:</b>\n5м, 15м, 30м, 1год, 4год, 1день\n\n<b>💡 Confidence:</b>\n0-100% = скільки індикаторів збігаються", reply_markup=reply_markup, parse_mode="HTML")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Аналізую... будь ласка чекай (10-15 сек)")
    data = query.data
    if data.startswith("mtf_"):
        symbol = data.replace("mtf_", "")
        result = await analyzer.multi_timeframe_analysis(symbol)
        keyboard = [[InlineKeyboardButton("🔄 Оновити", callback_data=f"mtf_{symbol}"), InlineKeyboardButton("⚡ Скан", callback_data=f"scan_{symbol}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=result, parse_mode="HTML", reply_markup=reply_markup)
    elif data.startswith("scan_"):
        symbol = data.replace("scan_", "")
        result = await analyzer.quick_scan(symbol)
        keyboard = [[InlineKeyboardButton("📊 Повний аналіз", callback_data=f"mtf_{symbol}"), InlineKeyboardButton("🔄 Оновити", callback_data=f"scan_{symbol}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=result, parse_mode="HTML", reply_markup=reply_markup)
    elif data.startswith("price_"):
        symbol = data.replace("price_", "")
        klines = await analyzer.get_klines(symbol, "60", limit=50)
        if klines:
            price = klines[-1]['close']
            change_24h = ((price - klines[0]['close']) / klines[0]['close']) * 100
            result = f"💰 <b>{symbol} Ціна</b>\n━━━━━━━━━━━\nЦіна: <code>${price:,.2f}</code>\n24h: <code>{change_24h:+.2f}%</code> {'📈' if change_24h > 0 else '📉'}\n\n<b>Дії:</b>\n<code>/analyze {symbol}</code>\n<code>/scan {symbol}</code>"
            keyboard = [[InlineKeyboardButton("📊 Мульти-ТФ", callback_data=f"mtf_{symbol}"), InlineKeyboardButton("⚡ Скан", callback_data=f"scan_{symbol}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=result, parse_mode="HTML", reply_markup=reply_markup)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Використання: /analyze BTC або /analyze ETH")
        return
    symbol = context.args[0].upper()
    msg = await update.message.reply_text(f"🔍 Аналізую {symbol}...")
    result = await analyzer.multi_timeframe_analysis(symbol)
    keyboard = [[InlineKeyboardButton("🔄 Оновити", callback_data=f"mtf_{symbol}"), InlineKeyboardButton("⚡ Швидкий скан", callback_data=f"scan_{symbol}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_text(result, parse_mode="HTML", reply_markup=reply_markup)

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Використання: /scan BTC або /scan ETH")
        return
    symbol = context.args[0].upper()
    msg = await update.message.reply_text(f"⚡ Сканую {symbol}...")
    result = await analyzer.quick_scan(symbol)
    keyboard = [[InlineKeyboardButton("📊 Повний аналіз", callback_data=f"mtf_{symbol}"), InlineKeyboardButton("🔄 Оновити", callback_data=f"scan_{symbol}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_text(result, parse_mode="HTML", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = "<b>📚 Команди:</b>\n\n/start - Меню\n/analyze BTC - Мультитаймфрейм\n/scan BTC - Швидкий скан\n/help - Справка\n\n<b>🎯 Confidence?</b>\n0-100% = скільки індикаторів\n\n<b>📊 Індикатори:</b>\n• RSI\n• MA\n• Williams Alligator\n• Price vs MA200"
    await update.message.reply_text(help_text, parse_mode="HTML")
    
    def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    logger.info("🤖 Бот запущено: Multi-Timeframe Analyzer")
    app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=[15, 2])

if __name__ == "__main__":
    main()
