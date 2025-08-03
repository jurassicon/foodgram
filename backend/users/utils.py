import datetime as dt

from config.settings import EMAIL_NAME_FROM
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail


def send_email_code(user):
    user.confirmation_code = default_token_generator.make_token(user)
    send_mail(
        subject='Код подтверждения',
        message=f'Ваш код подтверждения {user.confirmation_code}',
        from_email=EMAIL_NAME_FROM,
        recipient_list=[user.email, ],
        fail_silently=True,
    )
    user.save()
    return user


def validate_year(value):
    year = dt.date.today().year
    if not value <= year:
        raise ValidationError('Год выпуска не может быть больше текущего!')
