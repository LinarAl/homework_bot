"""Кастомные исключения."""


class ResponseError(Exception):
    """Ошибка при получении ответа с сервера."""

    pass


class ResponceStatusError(Exception):
    """Ошибка в ответе сервера, статус кода не 200."""

    pass


class ResponseContextError(Exception):
    """Ответ API не соответствует документации: отсутствует ожидаемый ключ."""

    pass


class SendMessageError(Exception):
    """Cбой при отправке сообщения в Telegram."""

    pass
