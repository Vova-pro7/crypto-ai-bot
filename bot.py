import os
import random
import telebot
from telebot import types

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

Thread(target=run).start()

def generate_signal():
    direction = random.choice(["⬆️ ВГОРУ (CALL)", "⬇️ ВНИЗ (PUT)"])
    probability = random.randint(65, 92)
    duration = random.choice([1, 2, 3, 5])
    return f"Сигнал: {direction}\nВпевненість: {probability}%\nЧас експірації: {duration} хв."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_btc = types.KeyboardButton("📊 Сигнал BTC")
    btn_eth = types.KeyboardButton("📊 Сигнал ETH")
    markup.add(btn_btc, btn_eth)
    bot.send_message(message.chat.id, "Бот готовий до роботи! Вибирай пару:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["📊 Сигнал BTC", "📊 Сигнал ETH"])
def send_crypto_signal(message):
    asset = "🪙 Bitcoin (BTC/USD)" if "BTC" in message.text else "🛡️ Ethereum (ETH/USD)"
    signal_text = generate_signal()
    full_message = f"**{asset}**\n\n{signal_text}"
    bot.send_message(message.chat.id, full_message, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()
