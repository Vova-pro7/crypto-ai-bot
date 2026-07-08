import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import requests
import pandas as pd

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

# Пари для легкого інфо-сервера CryptoCompare
MOCOINS = {
    'BTC': 'BTC',
    'ETH': 'ETH',
    'SOL': 'SOL',
    'BNB': 'BNB',
    'XRP': 'XRP'
}

# Таймфрейми (переводимо хвилини для запиту)
TIMEFRAMES = {
    '1м': '1',
    '5м': '5',
    '15м': '15',
    '30м': '30'
