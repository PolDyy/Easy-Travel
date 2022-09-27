from telebot import types
from bot_init import bot, storage
import requests
import datetime


@bot.message_handler(commands=['lowprice'])
def parameters(message):
    bot.send_message(message.from_user.id, 'В каком городе проводить поиск?')
    storage.set_state(message.chat.id, message.from_user.id, 'user')
    storage.reset_data(message.chat.id, message.from_user.id)
    bot.register_next_step_handler(message, get_city)


def get_city(message):
    try:
        url = "https://hotels4.p.rapidapi.com/locations/v2/search"

        querystring = {"query": message.text, "locale": "en_US", "currency": "USD"}

        headers = {
            "X-RapidAPI-Key": "2c58e305b4msh54bb0caa1eb94efp174209jsn2ada4f6b93e9",
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response_json = response.json()
        if response_json['moresuggestions'] != 0:
            storage.set_data(message.chat.id, message.from_user.id, 'city', response_json.get('suggestions')[0].get('entities')[0]
                             .get('destinationId'))
            bot.send_message(message.from_user.id, 'Введите дату заезда в формате ГГГГ-ММ-ДД:')
            bot.register_next_step_handler(message, get_date)
        else:
            bot.send_message(message.from_user.id, 'Город не найден. Проверьте правильность написание названия города')
            bot.register_next_step_handler(message, get_city)
    except AttributeError:
        get_city(message)


def get_date(message):
    data = storage.get_data(message.chat.id, message.from_user.id)
    if data.get('first_date'):
        try:
            second_date = datetime.datetime.strptime(message.text, '%Y-%m-%d')
            first_date = datetime.datetime.strptime(data['first_date'], '%Y-%m-%d')
            if second_date < first_date:
                raise TypeError
            storage.set_data(message.chat.id, message.from_user.id, 'second_date', message.text)
            storage.set_data(message.chat.id, message.from_user.id, 'days', (second_date - first_date).days)
            bot.send_message(message.from_user.id, 'Какое количество отелей вас интересует?')
            bot.register_next_step_handler(message, get_amount)
        except ValueError:
            bot.send_message(message.from_user.id, 'Проверьте правильность написания даты')
            bot.register_next_step_handler(message, get_date)
        except TypeError:
            bot.send_message(message.from_user.id, 'Выбранная вами дата должна быть позже текущей')
            bot.register_next_step_handler(message, get_date)
    else:
        try:
            first_date = datetime.datetime.strptime(message.text, '%Y-%m-%d')
            if first_date < datetime.datetime.now():
                raise TypeError
            storage.set_data(message.chat.id, message.from_user.id, 'first_date', message.text)
            bot.send_message(message.from_user.id, 'Выберете дату убытия')
            bot.register_next_step_handler(message, get_date)
        except ValueError:
            bot.send_message(message.from_user.id, 'Проверьте правильность написания даты')
            bot.register_next_step_handler(message, get_date)
        except TypeError:
            bot.send_message(message.from_user.id, 'Выбранная вами дата должна быть позже текущей')
            bot.register_next_step_handler(message, get_date)


def get_amount(message):
    try:
        amount = int(message.text)
        data = storage.get_data(message.chat.id, message.from_user.id)
        storage.set_data(message.chat.id, message.from_user.id, 'hotel_amount', amount)
        url = "https://hotels4.p.rapidapi.com/properties/list"

        querystring = {"destinationId": data['city'],
                       "pageNumber": "1", "pageSize": amount,
                       "checkIn": data['first_date'],
                       "checkOut": data['second_date'],
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
                          'url': hotel['urls'] if hotel['urls'] else 'Ссылка отсутствует',
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
        send_user_message(message)
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
        if amount != 0:
            for picture in response['hotelImages'][:amount]:
                picture_list.append(picture['baseUrl'].format(size='y'))
        hotel['picture_list'] = picture_list
    bot.send_message(message.from_user.id, "Отели найдены!")
    send_user_message(message)


def send_user_message(message):
    data = storage.get_data(message.chat.id, message.from_user.id)
    for hotel in data['hotels_list']:
        message_to_user = f'Отель: {hotel["name"]}\n ' \
                          f'Ссылка: {hotel["url"]}\n ' \
                          f'Даты поездки: c {data["first_date"]} по {data["second_date"]}\n' \
                          f'Цена за ночь: {hotel["night_price"]}$\n' \
                          f'Цена за тур: {hotel["all_price"]}$'
        if hotel.get('picture_list'):
            pictures = []
            for picture in hotel['picture_list']:
                if picture == hotel['picture_list'][0]:
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
