import telebot
from telebot import StateMemoryStorage
from sql_requests import init_db


token = '5606339525:AAFLABtOiFtu98-my4ACAJ9CT07yLBvjsyE'
storage = StateMemoryStorage()
bot = telebot.TeleBot(token, state_storage=storage)

init_db()


