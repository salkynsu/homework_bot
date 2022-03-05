import logging
import os
import sys
from dotenv import load_dotenv
from logging import StreamHandler
import requests
import telegram
import time
from http import HTTPStatus
import exceptions as ex

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение о новом статусе домашней работы."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'В чат отправлено сообщение {message}.')
    except ex.SendMessageFailureException('Ошибка отправки сообщения.'):
        logger.error(exc_info=True)


def get_api_answer(current_timestamp):
    """Получает ответ от API.
    Возвращает ответ, преобразованный в формат python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        logger.error(error, exc_info=True)
    if response.status_code != HTTPStatus.OK:
        raise ValueError(f'URL {ENDPOINT} недоступен.')
        logger.error(stack_info=True)
    response = response.json()
    return response


def check_response(response):
    """Проверяет полученный от API ответ.
    Возвращает список домашних работ.
    """
    if type(response) != dict:
        raise TypeError('Ответ от API имеет некорректный тип.')
        logger.error(stack_info=True)
    elif 'current_date' and 'homeworks' not in response.keys():
        raise ValueError('В ответе API нет ожидаемых ключей.')
        logger.error(stack_info=True)
    elif type(response['homeworks']) != list:
        raise TypeError('Домашние задания приходят не в виде списка.')
        logger.error(stack_info=True)
    elif len(response['homeworks']) == 0:
        homework = response.get('homeworks')
        return homework
        logger.debug('В ответе от API нет новых домашних заданий.')
    homework = response.get('homeworks')
    return homework


def parse_status(homework):
    """Вытаскивает из полученного ответа статус последней домашней работы.
    Возвращает сообщение, которое будет отправлено в чат.
    """
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе API не содержится ключ homework_name.'
        )
        logger.error(stack_info=True)
    homework_status = homework.get('status')
    if 'status' not in homework:
        raise KeyError(
            'В ответе API не содержится ключ status.'
        )
        logger.error(stack_info=True)
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise ValueError(
            f'Статус домашней работы {homework_status} некорректен.'
        )
        logger.error(stack_info=True)
    verdict = HOMEWORK_STATUSES[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def check_tokens():
    """Проверяет, есть ли все необходимые переменные.
    Прерывает работу скрипта, если не находит какую-то из переменных.
    """
    env_vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in env_vars:
        if token is None:
            return False
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}.'
                'Программа принудительно остановлена.'
            )
            sys.exit(0)
        else:
            return True


def main():
    """Основная логика работы бота."""
    logger.debug('Бот начал работу.')
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) != 0:
                homework = homework[0]
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error, exc_info=True)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
