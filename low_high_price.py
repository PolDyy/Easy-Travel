from telebot import types
from bot_init import bot, storage
from sql_requests import search_insert, save_mes_and_pict, save_mes, history_cleansing
from searching_params import search_type_buttons
from travel_bot_exceptions import DateError, ZeroOrNegativeNumber
from telegram_bot_calendar import DetailedTelegramCalendar
import requests
import datetime


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

