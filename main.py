from bot_init import bot
from telebot import types


@bot.message_handler(commands=['start'])
def start(message):
    start_message = "Привет, я твой помощник в подборе отелей в самых разных городах мира!Я и команда Too Easy Travel " \
                    "сделаем все для того чтобы твой отдых был комфортным. Если ты готов тогда давай приступим к поиску." \
                    "Чтобы узнать что я умею напиши: Help"
    bot.send_message(message.from_user.id, start_message, reply_markup=start_buttons())


@bot.message_handler(commands=['help', 'find'])
def search_type(message):
    if message.text == "/help":
        bot.send_message(message.from_user.id, "......")
    elif message.text == "/find":
        bot.send_message(message.from_user.id, "Какой параметр поиска выберете?", reply_markup=search_type_buttons())
    # elif message.text == "/lowprice":
    #     lowprice.parameters(message)
    # elif message.text == "/highprice":
    #     pass
    # elif message.text == "/bestdeal":
    #     pass
    # elif message.text == '/history':
    #     pass
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Выбери одну из кнопок.",
                         reply_markup=search_type_buttons())


def start_buttons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/find")
    btn2 = types.KeyboardButton("/help")
    markup.add(btn1, btn2)
    return markup


def search_type_buttons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/lowprice")
    btn2 = types.KeyboardButton("/highprice")
    btn3 = types.KeyboardButton("/bestdeal")
    btn4 = types.KeyboardButton("/history")
    btn5 = types.KeyboardButton("/help")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

import lowprice
bot.polling(none_stop=True, interval=0)
