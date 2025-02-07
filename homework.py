import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiException

from exceptions import ResponceStatusError, ResponseContextError, ResponseError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    encoding='utf-8',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s'
)


def check_tokens():
    """Проверка доступности переменных окружения."""
    list_token = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in list_token:
        if token is None:
            return False
    return True


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Удачная отправка сообщения в Telegram.')
    except ApiException as error:
        raise Exception(f'Cбой при отправке сообщения в Telegram: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params={'from_date': timestamp})
    except requests.RequestException as error:
        raise ResponseError(f'Ошибка при получении ответа с сервера{error}.')

    if response.status_code != HTTPStatus.OK:
        raise ResponceStatusError(
            f'Ошибка в ответе сервера, статус кода: {response.status_code}.')
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    response_key = 'homeworks'
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует документации: не dict.')

    if response_key not in response:
        raise ResponseContextError(
            'Ответ API не соответствует документации: '
            'отсутствует ожидаемый ключ')

    if not isinstance(response[response_key], list):
        raise TypeError('Ответ API не соответствует документации: не list.')
    return response[response_key]


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_keys = ['homework_name', 'status']

    if not isinstance(homework, dict):
        raise TypeError('Ответ API не соответствует документации: не dict.')

    for key in homework_keys:
        if key not in homework:
            raise ResponseContextError(
                f'Ответ API не соответствует документации: '
                f'отсутствует ожидаемый ключ "{key}".')

    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ResponseContextError(
            'Ответ API возвращает неожиданный статус домашней работы.')

    result = (
        f'Изменился статус проверки работы "{homework["homework_name"]}". '
        f'{HOMEWORK_VERDICTS[homework["status"]]}')
    return result


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None
    }

    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.'
        )
        sys.exit()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug('Нет домашних работ.')
                break
            for homework in homeworks:
                message = parse_status(homework)
                if last_send.get(homework['homework_name']) != message:
                    send_message(bot, message)
                    last_send[homework['homework_name']] = message
            timestamp = response.get('current_date')

        except Exception as error:
            logging.error(f'Ошибка: {error}')
            if 'Cбой при отправке сообщения в Telegram' in str(error):
                break
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
