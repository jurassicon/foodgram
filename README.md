# Foodgram — Grocery Assistant

Foodgram is a web application where users share recipes, follow favorite authors, add recipes to favorites, and generate a shopping list for selected recipes with the ability to download it as a single file.

## Demo

- Production: https://diddly-squat.ru/
- API root: https://diddly-squat.ru/api/
- API docs (ReDoc): https://diddly-squat.ru/docs/

## Tech stack

- Backend: Django, Django REST Framework, Djoser, django-filter
- Frontend: React (SPA, served by Nginx)
- Database: PostgreSQL
- Web server/static: Nginx
- Containerization: Docker, Docker Compose
- CI/CD: GitHub Actions (build → push → deploy)

## Quick start (Production, Docker Compose)

Requirements:
- Docker and Docker Compose v2 (plugin)

1) Clone the repository
```
git clone https://github.com/jurassicon/foodgram.git
cd foodgram
```

2) Create a `.env` file in the project root
Minimal example for docker-compose.production.yml:
```
# Django
SECRET_KEY=<django-secret>
DEBUG=False
ALLOWED_HOSTS=localhost 127.0.0.1 your.domain.com
CSRF_TRUSTED_ORIGINS=https://your.domain.com http://localhost
FRONTEND_URL=http://localhost

# Postgres (used by Django and the db container)
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram
POSTGRES_PASSWORD=<pg-password>
DB_HOST=db
DB_PORT=5432
```
Tips:
- `DB_HOST` must point to the DB service in compose — `db`.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` must include your domain/host.

3) Start the app
```
docker compose -f docker-compose.production.yml up -d
```

4) Initialize the backend (inside the container)
```
docker compose -f docker-compose.production.yml exec backend python manage.py makemigrations
```
```
docker compose -f docker-compose.production.yml exec backend python manage.py migrate --noinput
```
```
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic --no-input
```
```
docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser
```

5) Load reference data (ingredients/tags)
```
docker compose -f docker-compose.production.yml exec backend python recipes/scripts/import_data.py
```

After startup:
- Web UI: http://localhost/
- API: http://localhost/api/
- API docs: http://localhost/docs/

## Local development

For local development you can reuse the same compose file or your own environment. The main environment variables remain the same. Useful commands:
- Restart services: `docker compose -f docker-compose.production.yml restart backend gateway`
- Tail logs: `docker compose -f docker-compose.production.yml logs -f backend`

## User scenarios

- Sign up / sign in via e‑mail (Djoser)
- Create, edit, and delete your own recipes
- Browse the recipe feed and author profiles
- Subscribe to authors
- Add recipes to favorites
- Build and download a shopping list (TXT)

## Architecture and directories

- `backend/` — Django project (API, business logic)
- `frontend/` — frontend build (React); mounted into Nginx
- `gateway/` — Nginx configuration
- `backend/docs/` — static API documentation (ReDoc)
- `.github/workflows/` — CI/CD pipelines

## CI/CD (GitHub Actions)

The pipeline runs on push to the `main` branch and includes:
1. Lint (flake8) for the `backend/` folder.
2. Copy configs/docs to the server (SSH/SCP).
3. Build and push Docker images for `backend` and `frontend` to Docker Hub.
4. Deploy on the server: `docker compose down && docker compose up -d` and prune old images.

Required repository secrets:
- `HOST` — server IP/domain
- `USER` — SSH user
- `PRIVATE_KEY` — SSH private key
- `DOCKER_USERNAME`, `DOCKER_PASSWORD` — Docker Hub credentials
- App environment variables (see `.env`), optionally `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `TELEGRAM_TOKEN`, `TELEGRAM_TO` — for Telegram notifications (optional)

Note: secret names are aligned with `.github/workflows/main.yml` in this repo.

## Useful links

- Nginx configuration: `gateway/nginx.conf`
- Production compose: `docker-compose.production.yml`
- Django settings: `backend/config/settings.py`

## License

MIT License. See `LICENSE` for details.

## Author

Yuri Cherkasov — [Telegram](https://t.me/Iurii_Cherkasov)
