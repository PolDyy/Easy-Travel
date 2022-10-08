import telebot
from telebot import StateMemoryStorage
from sql_requests import init_db


token = ''
storage = StateMemoryStorage()
bot = telebot.TeleBot(token, state_storage=storage)

init_db()


