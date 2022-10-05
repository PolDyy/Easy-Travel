from bot_init import bot, storage
from telebot import types
from sql_requests import history_list


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def parameters(message: types.Message) -> None:
    """
    Функция определяет основные параметры поиска отелей
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    storage.set_state(message.chat.id, message.from_user.id, 'user')
    storage.reset_data(message.chat.id, message.from_user.id)
    storage.set_data(message.chat.id, message.from_user.id, 'max_pictures_amount', 5)
    storage.set_data(message.chat.id, message.from_user.id, 'max_hotels_amount', 10)
    if message.text == '/lowprice':
        from low_high_price import get_city
        storage.set_data(message.chat.id, message.from_user.id, 'search_key', "PRICE")
    elif message.text == '/highprice':
        from low_high_price import get_city
        storage.set_data(message.chat.id, message.from_user.id, 'search_key', "PRICE_HIGHEST_FIRST")
    elif message.text == "/bestdeal":
        from bestdeal import get_city
        storage.set_data(message.chat.id, message.from_user.id, 'search_key', "DISTANCE_FROM_LANDMARK")
    bot.send_message(message.from_user.id, 'В каком городе проводить поиск?\n (Название города на английском)')
    bot.register_next_step_handler(message, get_city)

@bot.message_handler(commands=['history'])
def history(message):
    mes_in_history = history_list(message)
    if mes_in_history:
        for message_tuple in mes_in_history:
            message_text, message_pictures = message_tuple
            if message_pictures is not None:
                message_pictures_list = message_pictures.split(" ,")
                pictures = []
                for picture in message_pictures_list:
                    if picture == message_pictures_list[0]:
                        pictures.append(types.InputMediaPhoto(media=picture, caption=message_text))
                    else:
                        pictures.append(types.InputMediaPhoto(media=picture))
                bot.send_media_group(message.from_user.id, media=pictures)
            else:
                bot.send_message(message.from_user.id, message_text)
        bot.send_message(message.from_user.id, 'Продолжим?', reply_markup=search_type_buttons())
    else:
        bot.send_message(message.from_user.id, 'Ваша история поиска пуста', reply_markup=search_type_buttons())


@bot.message_handler(commands=['help'])
def help(message):
    help_mes = 'Easy Travel - это бот позволяющий найти подходящие вам отели в любом городе мира!\n' \
               'В функиционал бота входят следующие команды:\n' \
               '1. Узнать топ самых дешёвых отелей в городе (команда /lowprice).\n'\
               '2. Узнать топ самых дорогих отелей в городе (команда /highprice).\n'\
               '3. Узнать топ отелей, наиболее подходящих по цене и расположению от центра (команда /bestdeal).\n'\
               '4. Узнать историю поиска отелей (команда /history)'
    bot.send_message(message.from_user.id, help_mes, reply_markup=search_type_buttons())

def search_type_buttons() -> types.ReplyKeyboardMarkup:
    """
    Формирует клавитуру главного меню
    :return:  Клавиатура главного меню"
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/lowprice")
    btn2 = types.KeyboardButton("/highprice")
    btn3 = types.KeyboardButton("/bestdeal")
    btn4 = types.KeyboardButton("/history")
    btn5 = types.KeyboardButton("/help")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup
