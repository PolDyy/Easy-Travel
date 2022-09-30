from bot_init import bot, storage
from telebot import types


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
    bot.send_message(message.from_user.id, 'В каком городе проводить поиск?')
    bot.register_next_step_handler(message, get_city)


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
