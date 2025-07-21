from django.core import exceptions

forbidden_usernames = ['me', 'admin', 'Gordon Ramsay', 'Андрей Макаревич']

def validate_username(value):
    if value.upper() == forbidden_usernames:
        raise exceptions.ValidationError('Выбранное имя недопустимо')
    return value
