from bot_init import bot
from telebot import types
import searching_params
from searching_params import search_type_buttons

@bot.message_handler(commands=['start'])
def start(message: types.Message) -> None:
    """
    Функиция приветствия пользователя
    :param message: Сообщение от пользователя
    :ptype: message: types.Message
    :return:
    """
    start_message = "Привет, я твой помощник в подборе отелей в самых разных городах мира!Я и команда Too Easy Travel " \
                    "сделаем все для того чтобы твой отдых был комфортным. Если ты готов тогда давай приступим к поиску." \
                    "Чтобы узнать что я умею напиши: Help"
    bot.send_message(message.from_user.id, start_message, reply_markup=start_buttons())


@bot.message_handler(commands=['help', 'menu'])
def search_type(message: types.Message) -> None:
    """
    Функиция предлагает пользователю ознакомиться с функционалом чат-бота или перейти к меню
    :param message: Сообщение от пользователя
    :ptype: message: types.Message
    :return:
    """
    if message.text == "/help":
        bot.send_message(message.from_user.id, "......")
    elif message.text == "/menu":
        bot.send_message(message.from_user.id, "Какой параметр поиска выберете?", reply_markup=search_type_buttons())
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Выбери одну из кнопок.",
                         reply_markup=search_type_buttons())


def start_buttons() -> types.ReplyKeyboardMarkup:
    """
    Формирует клавитуру предлгающую ознакомиться пользователю с функционалом чат-бота или перейти в меню
    :return:  Клавиатура предлгающая ознакомиться пользователю с функционалом чат-бота или перейти в меню
    :return:
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/menu")
    btn2 = types.KeyboardButton("/help")
    markup.add(btn1, btn2)
    return markup


bot.polling(none_stop=True, interval=0)
