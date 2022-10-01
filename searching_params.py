from bot_init import bot, storage
from telebot import types
import sqlite3


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

@bot.message_handler(commands=['history'])
def history(message):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    history_list = cur.execute(""" SELECT message, pictures
    FROM messages
    WHERE messages.search_id IN(SELECT search_id FROM searches 
    LEFT JOIN users ON users.user_id = searches.user_id)
    """).fetchall()
    len_list = cur.execute("""SELECT COUNT(search_id)
    FROM searches
    GROUP BY user_id
    HAVING user_id = :user_id
    """, {"user_id": message.from_user.id}).fetchall()
    conn.close()
    if history_list:
        conn = sqlite3.connect('travel_bot.db')
        cur = conn.cursor()
        if int(len_list[0][0]) > 3:
            cur.execute("""DELETE FROM searches
             WHERE search_id = (SELECT MIN(search_id) FROM searches 
             WHERE user_id = :user_id)""", {"user_id": message.from_user.id})
        conn.commit()
        conn.close()
        for message_tuple in history_list:
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
