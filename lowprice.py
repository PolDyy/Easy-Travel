from telebot import types
from bot_init import bot, storage


@bot.message_handler(content_types='text', commands=['/lowprice'])
def parameters(message):
    bot.send_message(message.from_user.id, 'В какоом городе проводить поиск?')
    storage.set_state(message.chat.id, message.from_user.id, 'user')
    bot.register_next_step_handler(message, get_amount)


def get_amount(message):
    storage.set_data(message.chat.id, message.from_user.id, 'city', message.text)
    print(storage.get_data(message.chat.id, message.from_user.id))
    bot.send_message(message.from_user.id, 'Какое количество отелей?')
    amount = 0
    while amount == 0:
        try:
            amount = int(message.text)
            storage.set_data(message.chat.id, message.from_user.id, 'hotel_amount', amount)
        except ValueError:
            bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
    bot.register_next_step_handler(message, get_picture)


def get_picture(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да")
    btn2 = types.KeyboardButton("Нет")
    markup.add(btn1, btn2)
    bot.send_message(message.from_user.id, 'Вам нужны фотографии отелей?', reply_markup=markup)
    if message.text == "Да":
        bot.register_next_step_handler(message, get_picture_amount)
    elif message.text == "Нет":
        storage.set_data(message.chat.id, message.from_user.id, 'pictures_amount', 0)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Выбери одну из кнопок.",
                         reply_markup=markup)


def get_picture_amount(message):
    max_amount = 5
    pictures_amount = 0
    bot.send_message(message.from_user.id, f'В каком количестве нужны фотографии? (Максимально {max_amount})')
    while pictures_amount == 0:
        try:
            if int(message.text) <= max_amount:
                pictures_amount = int(message.text)
                storage.set_data(message.chat.id, message.from_user.id, 'pictures_amount', pictures_amount)
            else:
                bot.send_message(message.from_user.id, f'Количество запрашиваемых фотографий не должно превышать '
                                                       f'{max_amount}')
        except ValueError:
            bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
    print(storage.get_data(message.chat.id, message.from_user.id))


