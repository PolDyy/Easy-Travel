import telebot
from telebot import StateMemoryStorage
import sqlite3


token = '5606339525:AAFLABtOiFtu98-my4ACAJ9CT07yLBvjsyE'
storage = StateMemoryStorage()
bot = telebot.TeleBot(token, state_storage=storage)


conn = sqlite3.connect('travel_bot.db')
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(
   user_id INTEGER PRIMARY KEY NOT NULL UNIQUE,
   user_name TEXT
);
""")
cur.execute("""CREATE TABLE IF NOT EXISTS searches(
   search_id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
   user_id INTEGER REFERENCES users(user_id) NOT NULL
);
""")
cur.execute("""CREATE TABLE IF NOT EXISTS messages(
   search_id INTEGER REFERENCES searches(search_id) NOT NULL,
   message TEXT NOT NULL,
   pictures TEXT
);
""")
conn.commit()
conn.close()
