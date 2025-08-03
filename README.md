# Foodgram - Продуктовый помощник

## Описание проекта

Foodgram - это веб-приложение "Продуктовый помощник", которое позволяет пользователям публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а также формировать список покупок для выбранных рецептов и скачивать его.

## Технологии

- **Бэкенд**: Django, Django REST Framework
- **Фронтенд**: React
- **База данных**: PostgreSQL
- **Контейнеризация**: Docker, docker-compose
- **Веб-сервер**: Nginx
- **CI/CD**: GitHub Actions

## Системные требования

- Docker
- Docker Compose

## Установка и запуск

### Локальная разработка

1. Клонируйте репозиторий:
   ```
   git clone https://github.com/your-username/foodgram.git
   cd foodgram
   ```

2. Создайте файл `.env` в корневой директории проекта со следующими переменными:
   ```
   DEBUG=False
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
   
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   DB_HOST=db
   DB_PORT=5432
   ```

3. Запустите проект с помощью Docker Compose:
   ```
   docker-compose up -d
   ```

4. После запуска проект будет доступен по адресу: http://localhost

### Доступ к API и документации

- **API**: http://localhost/api/
- **Документация API**: http://localhost/api/docs/

5. После запуска можно наполнить БД ингридиентами и импортировать теги.
   ```
   docker-compose exec backend python manage.py makemigrations
   ```
   ```
   docker-compose exec backend python manage.py migrate --noinput
   ```
   ```
   docker-compose exec backend python manage.py collectstatic --no-input
   ```
   ```
   docker-compose exec backend python manage.py createsuperuser
   ```

## Использование

### Регистрация и авторизация

Для использования всех возможностей сервиса необходимо зарегистрироваться. После регистрации вы сможете:

- Создавать, редактировать и удалять собственные рецепты
- Просматривать рецепты других пользователей
- Добавлять рецепты в избранное
- Подписываться на других авторов
- Формировать список покупок

### Работа со списком покупок

1. Добавьте интересующие вас рецепты в список покупок
2. Перейдите в раздел "Список покупок"
3. Нажмите кнопку "Скачать список" для получения PDF-файла с необходимыми ингредиентами

## Деплой на сервер

Проект настроен для автоматического деплоя на сервер с использованием GitHub Actions.

1. Настройте следующие секреты в вашем GitHub репозитории:
   - `HOST` - IP-адрес вашего сервера
   - `USERNAME` - имя пользователя для SSH-подключения
   - `PRIVATE_KEY` - приватный SSH-ключ
   - `DOCKER_USER` - имя пользователя Docker Hub
   - `DOCKER_PASS` - пароль от Docker Hub
   - Все переменные окружения из файла `.env`
   - `TELEGRAM_TO` и `TELEGRAM_TOKEN` (опционально, для уведомлений)

2. При пуше в ветку `master` будет запущен процесс CI/CD:
   - Сборка и публикация образов в Docker Hub
   - Деплой на сервер
   - Отправка уведомления в Telegram (если настроено)

## Структура проекта

- `backend/` - Django-приложение (API)
- `frontend/` - React-приложение
- `gateway/` - Конфигурация Nginx
- `docs/` - Документация API
- `.github/workflows/` - Конфигурация CI/CD

## Автор

Юрий Черкасов  [GitHub](https://github.com/jurassicon)

## Лицензия

Этот проект лицензирован под MIT License - подробности см. в файле LICENSE.