# Deployment

## Environment

1. Copy `.env.example` to `.env` at the repository root for Docker deployments.
2. For local Django commands, you can also copy the same values to `backend/.env`.
3. Set `DJANGO_ENV=production`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` before deploying.

## Docker Compose

Run the full stack with:

```bash
docker compose up -d --build
```

Services included:

- `web`: Django + Gunicorn
- `worker`: `django-q` cluster
- `db`: PostgreSQL 15
- `redis`: Redis 7
- `nginx`: reverse proxy for app traffic plus static and media files

## Health Checks

- `GET /health/` is public and returns database, cache, and disk status.
- `GET /metrics/` is restricted to audit-capable users and returns lightweight system counts.

## Manual Deploy Steps

If you are deploying outside Docker, run the setup commands once, then start the web and worker processes separately:

```bash
cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Web process:

```bash
cd backend
gunicorn --bind 0.0.0.0:8000 config.wsgi:application
```

Worker process:

```bash
cd backend
python manage.py qcluster
```

## Safe Bootstrap Options

- Set `CREATE_SUPERUSER=true` only when you also provide the `DJANGO_SUPERUSER_*` variables.
- Set `LOAD_FIXTURES=true` and `FIXTURE_PATH=/path/to/fixture.json` only when you explicitly want fixtures loaded during deploy.
