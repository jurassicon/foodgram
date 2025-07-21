from django.core import exceptions

forbidden_usernames = ['me', 'admin', 'Gordon Ramsay', 'Андрей Макаревич']

def validate_username(value):
    normalized = value.strip().lower()
    forbidden_normalized = [name.lower() for name in forbidden_usernames]
    if normalized in forbidden_normalized:
        raise exceptions.ValidationError(
            f'Имя: {normalized} недопустимо'
        )
    return value
