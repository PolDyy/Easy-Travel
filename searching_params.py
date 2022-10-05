from bot_init import bot, storage
from telebot import types
from sql_requests import history_list
from sql_requests import search_insert, save_mes_and_pict, save_mes, history_cleansing
from travel_bot_exceptions import DateError, ZeroOrNegativeNumber
from telegram_bot_calendar import DetailedTelegramCalendar
import re
import requests
import datetime
from typing import Callable


def is_a_command(func: Callable) -> Callable:
    """Декоратор проверяющий не ввел ли пользователь команду во время поиска"""
    def wrapped_func(message: types.Message) -> None:
        if message.text in ['/menu', '/lowprice', '/highprice', '/bestdeal', '/history', '/help', '/start']:
            bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
            bot.send_message(message.from_user.id, "Введенная вами команда прервала поиск. Мы вернули вас в главное меню",
                             reply_markup=search_type_buttons())
        else:
            func(message)
    return wrapped_func


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
        storage.set_data(message.chat.id, message.from_user.id, 'search_key', "PRICE")
    elif message.text == '/highprice':
        storage.set_data(message.chat.id, message.from_user.id, 'search_key', "PRICE_HIGHEST_FIRST")
    elif message.text == "/bestdeal":
        storage.set_data(message.chat.id, message.from_user.id, 'search_key', "DISTANCE_FROM_LANDMARK")
    bot.send_message(message.from_user.id, 'В каком городе проводить поиск?\n (Название города на английском)')
    bot.register_next_step_handler(message, get_city)


@is_a_command
def get_city(message: types.Message) -> None:
    """
    Отправляет запрос с городом, введенным пользователем, и сохраняет id города в storage.
    Инициализирует получение от пользователя дат.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    data = storage.get_data(message.chat.id, message.from_user.id)
    if data.get('first_date'):
        del data['first_date']
    try:
        url = "https://hotels4.p.rapidapi.com/locations/v2/search"

        querystring = {"query": message.text, "locale": "en_US", "currency": "USD"}

        headers = {
            "X-RapidAPI-Key": "2c58e305b4msh54bb0caa1eb94efp174209jsn2ada4f6b93e9",
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response_json = response.json()
        if response_json.get('suggestions')[0].get('entities'):
            storage.set_data(message.chat.id, message.from_user.id, 'city', response_json.get('suggestions')[0].get('entities')[0]
                             .get('destinationId'))
            bot.send_message(message.from_user.id, 'Введите дату заезда')
            get_date(message)
        else:
            bot.send_message(message.from_user.id, 'Город не найден. Проверьте правильность написание названия города')
            bot.register_next_step_handler(message, get_city)
    except AttributeError:
        get_city(message)


def get_date(message: types.Message) -> None:
    """
    Инициализирует клавиатуру выбора даты
    :param message:
    :ptype: types.Message
    :return: None
    """
    calendar, step = DetailedTelegramCalendar(min_date=datetime.date.today(), locale='ru').build()
    LSTEP = {"y": "год", "m": 'месяц', "d": "день"}
    bot.send_message(message.chat.id, f"Выберете {LSTEP[step]}", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c: types.CallbackQuery) -> None:
    """
    Обрабатывает резуьтаты нажатия пользователем на клавиатуру календаря
    :param c: Объект запроса обртатного вызова
    :ptype: types.CallbackQuery
    :return: None
    """
    try:
        result, key, step = DetailedTelegramCalendar(min_date=datetime.date.today(), locale='ru').process(c.data)
        LSTEP = {"y": "год", "m": 'месяц', "d": "день"}
        data = storage.get_data(c.message.chat.id, c.from_user.id)
        if not result and key:
            bot.edit_message_text(f"Выберете {LSTEP[step]}:",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=key)
        elif result:
            bot.edit_message_text(f"Вы выбрали {result}",
                                  c.message.chat.id, c.message.message_id)
            if data.get('first_date'):
                first_date = datetime.date.fromisoformat(data['first_date'])
                if result < first_date:
                    raise DateError
                storage.set_data(c.message.chat.id, c.from_user.id, 'second_date', result.strftime('%Y-%m-%d'))
                storage.set_data(c.message.chat.id, c.from_user.id, 'days',
                                 (result - first_date).days)
                if data['search_key'] =="DISTANCE_FROM_LANDMARK":
                    bot.send_message(c.from_user.id, 'Введите диапазон цен в долларах за ночь?(Формат ввода:20-240)')
                    bot.register_next_step_handler(c.message, get_price_range)
                else:
                    bot.send_message(c.from_user.id,
                                     f'Какое количество отелей вас интересует?(Не более {data["max_hotels_amount"]})')
                    bot.register_next_step_handler(c.message, get_amount)
            else:
                storage.set_data(c.message.chat.id, c.from_user.id, 'first_date', result.strftime('%Y-%m-%d'))
                bot.send_message(c.from_user.id, 'Выберете дату убытия:')
                get_date(c.message)
    except DateError:
        bot.send_message(c.from_user.id, 'Выбранная вами дата убытия должна быть позже даты заезда')
        del storage.get_data(c.message.chat.id, c.from_user.id)['first_date']
        bot.send_message(c.from_user.id, 'Выберете дату заезда:')
        get_date(c.message)


@is_a_command
def get_price_range(message: types.Message) -> None:
    """
    Обрабатывает сообщение от пользователя с ценновым диапазоном.
    Инициализирует получение от пользователя информацию о желаемом расстоянии между центром города и отелем
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    if re.fullmatch(r'\d{1,10}(-|\s-\s)\d{1,10}', message.text):
        min_price, max_price = message.text.split('-')
        if max_price >= min_price:
            storage.set_data(message.chat.id, message.from_user.id, 'min_price', int(min_price))
            storage.set_data(message.chat.id, message.from_user.id, 'max_price', int(max_price))
        else:
            storage.set_data(message.chat.id, message.from_user.id, 'min_price', int(max_price))
            storage.set_data(message.chat.id, message.from_user.id, 'max_price', int(min_price))
        bot.send_message(message.from_user.id, 'На каком  максимальном расстоянии от центра города (в милях) '
                                               'должен быть расположен отель?')
        bot.register_next_step_handler(message, get_miles)
    else:
        bot.send_message(message.from_user.id, 'Проверьте правильность написания диапазона цен')
        bot.register_next_step_handler(message, get_date)


@is_a_command
def get_miles(message: types.Message) -> None:
    """
    Обрабатывает информацию о расстоянии между отелем и центром города.
    Инициализирует получение от пользователя информации о необходимом количестве отелей.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    mes = message.text
    data = storage.get_data(message.chat.id, message.from_user.id)
    if ',' in mes:
        mes = '.'.join(mes.split(','))
    try:
        mes = float(mes)
        storage.set_data(message.chat.id, message.from_user.id, 'miles', mes)
        bot.send_message(message.from_user.id,
                         f'Какое количество отелей вас интересует?(Не более {data["max_hotels_amount"]})')
        bot.register_next_step_handler(message, get_amount)
    except ValueError:
        bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
        bot.register_next_step_handler(message, get_miles)


@is_a_command
def get_amount(message: types.Message) -> None:
    """
    Выполняет запрос на получение информации об отелях
    Формирует список с  необходимым пользователю количеством отелей и сохраняет его в storage.
    Инициализирует получение информации от пользователя в необходимости фотографий.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    try:
        data = storage.get_data(message.chat.id, message.from_user.id)
        amount = int(message.text)
        if amount <= 0:
            raise ZeroOrNegativeNumber
        if amount <= data['max_hotels_amount']:
            storage.set_data(message.chat.id, message.from_user.id, 'hotel_amount', amount)
            url = "https://hotels4.p.rapidapi.com/properties/list"
            if data['search_key'] == "DISTANCE_FROM_LANDMARK":
                querystring = {"destinationId": data['city'],
                               "pageNumber": "1", "pageSize": amount,
                               "checkIn": data['first_date'],
                               "checkOut": data['second_date'],
                               "adults1": "1", 'priceMin': data["min_price"], 'priceMax': data["max_price"],
                               "sortOrder": data['search_key'], "locale": "en_US", "currency": "USD"}
            else:
                querystring = {"destinationId": data['city'],
                               "pageNumber": "1", "pageSize": amount,
                               "checkIn": data['first_date'],
                               "checkOut": data['second_date'],
                               "adults1": "1", "sortOrder": data['search_key'], "locale": "en_US", "currency": "USD"}

            headers = {
                "X-RapidAPI-Key": "2c58e305b4msh54bb0caa1eb94efp174209jsn2ada4f6b93e9",
                "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
            }
            response = requests.request("GET", url, headers=headers, params=querystring).json()
            hotels_list_data = []
            for hotel in response['data']['body']['searchResults']['results']:
                if data['search_key'] == "DISTANCE_FROM_LANDMARK":
                    hotel_data = {'id': hotel['id'],
                                  'name': hotel['name'],
                                  'url': hotel['urls'] if hotel['urls'] else 'Ссылка отсутствует',
                                  'night_price': hotel['ratePlan']['price']['exactCurrent'],
                                  'all_price': round(data['days'] * hotel['ratePlan']['price']['exactCurrent'], 2),
                                  'miles': hotel['landmarks'][0]['distance'].split(' ')[0]
                                  }
                else:
                    hotel_data = {'id': hotel['id'],
                                  'name': hotel['name'],
                                  'url': hotel['urls'] if hotel['urls'] else 'Ссылка отсутствует',
                                  'night_price': hotel['ratePlan']['price']['exactCurrent'],
                                  'all_price': round(data['days'] * hotel['ratePlan']['price']['exactCurrent'], 2)
                                  }
                hotels_list_data.append(hotel_data)
            if hotels_list_data:
                storage.set_data(message.chat.id, message.from_user.id, 'hotels_list', hotels_list_data)
                bot.send_message(message.from_user.id, 'Вам нужны фотографии отелей?', reply_markup=yes_no_buttons())
                bot.register_next_step_handler(message, get_picture)
            else:
                bot.send_message(message.from_user.id, 'К сожалению предложений согласно вашим парамметрам найдено'
                                                       ' не было. Повторить поиск с указанием новых парамметров?',
                                 reply_markup=yes_no_buttons())
                bot.register_next_step_handler(message, no_find_hotels)
        else:
            bot.send_message(message.from_user.id, f'Количество запрашиваемых отелей не должно превышать '
                                                   f'{data["max_hotels_amount"]}')
            bot.register_next_step_handler(message, get_amount)
    except ValueError:
        bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
        bot.register_next_step_handler(message, get_amount)
    except ZeroOrNegativeNumber:
        bot.send_message(message.from_user.id, 'Вводимое вами число должно быть положительным числом')
        bot.register_next_step_handler(message, get_amount)


@is_a_command
def get_picture(message: types.Message) -> None:
    """
    Зависимости от ответа пользователя инициализирует функцию получения  от пользователя необходимого
    количества фотографий или функцию формирования и отправу сообщений с отелями.
    :ptype: types.Message
    :return: None
    """
    max_amount = storage.get_data(message.chat.id, message.from_user.id)['max_pictures_amount']
    if message.text == "Да":
        bot.send_message(message.from_user.id, f'В каком количестве нужны фотографии? (Максимально {max_amount})')
        bot.register_next_step_handler(message, get_picture_amount)

    elif message.text == "Нет":
        send_user_message(message)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Выбери одну из кнопок.",
                         reply_markup=yes_no_buttons())
        bot.register_next_step_handler(message, get_picture)


@is_a_command
def get_picture_amount(message: types.Message) -> None:
    """
    Обработывает полученную информацию о количестве фотографий.
    Инициализирует функцию получения фотографий.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    max_amount = storage.get_data(message.chat.id, message.from_user.id)['max_pictures_amount']
    try:
        pictures_amount = int(message.text)
        if pictures_amount <= 0:
            raise ZeroOrNegativeNumber
        if pictures_amount <= max_amount:
            pictures_append(message, pictures_amount)
        else:
            bot.send_message(message.from_user.id, f'Количество запрашиваемых фотографий не должно превышать '
                                                   f'{max_amount}')
            bot.register_next_step_handler(message, get_picture_amount)
    except ValueError:
        bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
        bot.register_next_step_handler(message, get_picture_amount)
    except ZeroOrNegativeNumber:
        bot.send_message(message.from_user.id, 'Вводимое вами число должно быть положительным числом')
        bot.register_next_step_handler(message, get_picture_amount)


def pictures_append(message: types.Message, amount: int) -> None:
    """
    Выполняет запрос на получение фотографий.
    Формирует список с  необходимым пользователю количествои фотографий и сохраняет его в storage.
    Инициализирует отправку сообщения пользователю с информацией об отелях.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :param amount: Количество фотографий
    :ptype: int
    :return: None
    """
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
    send_user_message(message)


def send_user_message(message: types.Message) -> None:
    """
    Формирует и отправляет сообщения пользователю с информацией о найденных отелях.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    search_insert(message)
    data = storage.get_data(message.chat.id, message.from_user.id)
    for hotel in data['hotels_list']:
        if data['search_key'] == "DISTANCE_FROM_LANDMARK":
            message_to_user = f'Отель: {hotel["name"]}\n' \
                              f'Ссылка: {hotel["url"]}\n' \
                              f'Даты поездки: c {data["first_date"]} по {data["second_date"]}\n' \
                              f'Цена за ночь: {hotel["night_price"]}$\n' \
                              f'Цена за тур: {hotel["all_price"]}$\n' \
                              f'Удаленность от центра: {hotel["miles"]} в милях'
            if float(hotel["miles"]) > data['miles']:
                message_to_user = '\n'.join(
                    ("Обратите внимание!\nОтель расположен на большем расстоянии, чем требовалось.", message_to_user))
        else:
            message_to_user = f'Отель: {hotel["name"]}\n' \
                              f'Ссылка: {hotel["url"]}\n' \
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
            save_mes_and_pict(message, message_to_user, hotel['picture_list'])

        else:
            save_mes(message, message_to_user)
            bot.send_message(message.from_user.id, message_to_user)
    history_cleansing(message)
    bot.send_message(message.from_user.id, "Продолжим поиск?", reply_markup=search_type_buttons())


def no_find_hotels(message: types.Message) -> None:
    """
    Обрабатывает случай, когда не было найдено ни одного отеля. В зависимости от ответа пользователя начинает поиск
    заново или переводит пользователя в главное меню.
    :param message: Сообщение полученное от пользователя
    :ptype: types.Message
    :return: None
    """
    if message.text == "Нет":
        bot.send_message(message.from_user.id, "Какой параметр поиска выберете?", reply_markup=search_type_buttons())
    elif message.text == "Да":
        bot.send_message(message.from_user.id, 'В каком городе проводить поиск?')
        bot.register_next_step_handler(message, get_city)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Выбери одну из кнопок.",
                         reply_markup=yes_no_buttons())
        bot.register_next_step_handler(message, no_find_hotels)


def yes_no_buttons() -> types.ReplyKeyboardMarkup:
    """
    Формирует клавитуру с клавишами "Да" или "Нет"
    :return:  Клавиатура с клавишами "Да" или "Нет"
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да")
    btn2 = types.KeyboardButton("Нет")
    markup.add(btn1, btn2)
    return markup


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
