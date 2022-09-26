from telebot import types
from bot_init import bot, storage
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
import requests
import time


@bot.message_handler(commands=['lowprice'])
def parameters(message):
    bot.send_message(message.from_user.id, 'В каком городе проводить поиск?')
    storage.set_state(message.chat.id, message.from_user.id, 'user')
    storage.reset_data(message.chat.id, message.from_user.id)
    bot.register_next_step_handler(message, get_city)


def get_city(message):
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"

    querystring = {"query": message.text, "locale": "en_US", "currency": "USD"}

    headers = {
        "X-RapidAPI-Key": "2c58e305b4msh54bb0caa1eb94efp174209jsn2ada4f6b93e9",
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring).json()
    storage.set_data(message.chat.id, message.from_user.id, 'city', response['suggestions'][0]['entities'][0]['destinationId'])
    bot.register_next_step_handler(message, get_date)


def get_date(message):
    # Клавиатура не сразу открывается. Нужно отправить любое другое сообщение
    calendar, step = DetailedTelegramCalendar(locale='ru').build()
    bot.send_message(message.chat.id,
                     f"Выберете {LSTEP[step]}", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c):
    result, key, step = DetailedTelegramCalendar().process(c.data)
    data = storage.get_data(c.message.chat.id, c.message.from_user.id) # Выводит NONE
    if not result and key:
        bot.edit_message_text(f"Выберете {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Вы выбрали {result}",
                              c.message.chat.id, c.message.message_id)
        if data.get('first_date'):
            storage.set_data(c.message.chat.id, c.message.from_user.id, 'second_date', time.strftime('%Y-%m-%d', result))
            storage.set_data(c.message.chat.id, c.message.from_user.id, 'days', (time.strftime('%Y-%m-%d', result) - data['first_date']))
            bot.send_message(c.message.from_user.id, 'Какое количество отелей вас интересует?')
            bot.register_next_step_handler(c.message, get_amount)
        else:
            storage.set_data(c.message.chat.id, c.message.from_user.id, 'first_date', time.strftime('%Y-%m-%d', result))
            bot.send_message(c.message.from_user.id, 'Выберете дату убытия')
            bot.register_next_step_handler(c.message, get_date)


def get_amount(message):
    try:
        amount = int(message.text)
        data = storage.get_data(message.chat.id, message.from_user.id)
        storage.set_data(message.chat.id, message.from_user.id, 'hotel_amount', amount)
        print(data)
        url = "https://hotels4.p.rapidapi.com/properties/list"

        querystring = {"destinationId": data['city'],
                       "pageNumber": "1", "pageSize": amount,
                       "checkIn": data['first_date'],
                       "checkOut": data(message.chat.id, message.from_user.id)['second_date'],
                       "adults1": "1", "sortOrder": "PRICE", "locale": "en_US", "currency": "USD"}

        headers = {
            "X-RapidAPI-Key": "2c58e305b4msh54bb0caa1eb94efp174209jsn2ada4f6b93e9",
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }
        response = requests.request("GET", url, headers=headers, params=querystring).json()

        hotels_list_data = []
        for hotel in response['data']['body']['searchResults']['results']:
            hotel_data = {'id': hotel['id'],
                          'name': hotel['name'],
                          'url': hotel['thumbnailUrl'],
                          'night_price': hotel['ratePlan']['price']['exactCurrent'],
                          'all_price': data['days'] * hotel['ratePlan']['price']['exactCurrent']
                          }
            hotels_list_data.append(hotel_data)

        storage.set_data(message.chat.id, message.from_user.id, 'hotels_list', hotels_list_data)
        bot.send_message(message.from_user.id, 'Вам нужны фотографии отелей?', reply_markup=yes_no_buttons())
        bot.register_next_step_handler(message, get_picture)
    except ValueError:
        bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
        bot.register_next_step_handler(message, get_amount)


def get_picture(message):
    max_amount = 5
    if message.text == "Да":
        bot.send_message(message.from_user.id, f'В каком количестве нужны фотографии? (Максимально {max_amount})')
        bot.register_next_step_handler(message, get_picture_amount)

    elif message.text == "Нет":
        pictures_append(message, 0)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Выбери одну из кнопок.",
                         reply_markup=yes_no_buttons())
        bot.register_next_step_handler(message, get_picture)


def get_picture_amount(message):
    max_amount = 5
    try:
        if int(message.text) <= max_amount:
            pictures_amount = int(message.text)
            pictures_append(message, pictures_amount)
        else:
            bot.send_message(message.from_user.id, f'Количество запрашиваемых фотографий не должно превышать '
                                                   f'{max_amount}')
            bot.register_next_step_handler(message, get_picture_amount)
    except ValueError:
        bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
        bot.register_next_step_handler(message, get_picture_amount)


def pictures_append(message, amount):
    for hotel in storage.get_data(message.chat.id, message.from_user.id)['hotels_list']:
        url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

        querystring = {"id": hotel['id']}

        headers = {
            "X-RapidAPI-Key": "2c58e305b4msh54bb0caa1eb94efp174209jsn2ada4f6b93e9",
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring).json()
        picture_list = []
        if amount == 0:
            for picture in response['hotelImages']:
                picture_list.append(picture['baseUrl'].formst(size='y'))
        hotel['picture_list'] = picture_list
        bot.register_next_step_handler(message, send_message)


def send_message(message):
    data = storage.get_data(message.chat.id, message.from_user.id)
    for hotel in data['hotels_list']:
        message_to_user = f'Отель: {hotel["name"]}\n ' \
                          f'Ссылка: {hotel["url"]}\n ' \
                          f'Даты поездки: c {data["first_date"]} по {data["second_date"]}' \
                          f'Цена за ночь: {hotel["night_price"]}' \
                          f'Цена за тур: {hotel["all_price"]}'
        if data['hotels_list']['picture_list']:
            pictures = []
            for picture in data['hotels_list']['picture_list']:
                if picture == data['hotels_list']['picture_list'][0]:
                    pictures.append(types.InputMediaPhoto(media=picture, caption=message_to_user))
                else:
                    pictures.append(types.InputMediaPhoto(media=picture))
            bot.send_media_group(message.from_user.id, media=pictures)
        else:
            bot.send_message(message.from_user.id, message_to_user)


def yes_no_buttons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да")
    btn2 = types.KeyboardButton("Нет")
    markup.add(btn1, btn2)
    return markup
