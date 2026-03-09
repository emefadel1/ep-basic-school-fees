#!/bin/sh
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -d "/app/backend" ]; then
  APP_DIR="/app/backend"
elif [ -d "$SCRIPT_DIR/../backend" ]; then
  APP_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../backend" && pwd)
else
  echo "Unable to locate backend directory for deployment."
  exit 1
fi

cd "$APP_DIR"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${LOAD_FIXTURES:-false}" = 'true' ]; then
  if [ -n "${FIXTURE_PATH:-}" ] && [ -f "${FIXTURE_PATH}" ]; then
    python manage.py loaddata "${FIXTURE_PATH}"
  fi
fi

if [ "${CREATE_SUPERUSER:-false}" = 'true' ]; then
  if [ -z "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
    echo 'CREATE_SUPERUSER=true but DJANGO_SUPERUSER_USERNAME is missing'
    exit 1
  fi
  if [ -z "${DJANGO_SUPERUSER_EMAIL:-}" ]; then
    echo 'CREATE_SUPERUSER=true but DJANGO_SUPERUSER_EMAIL is missing'
    exit 1
  fi
  if [ -z "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo 'CREATE_SUPERUSER=true but DJANGO_SUPERUSER_PASSWORD is missing'
    exit 1
  fi
  python manage.py shell -c "from django.contrib.auth import get_user_model; import os; User = get_user_model(); username = os.environ.get('DJANGO_SUPERUSER_USERNAME'); email = os.environ.get('DJANGO_SUPERUSER_EMAIL'); password = os.environ.get('DJANGO_SUPERUSER_PASSWORD'); existing = User.objects.filter(username=username).first(); existing or User.objects.create_superuser(username, email, password)"
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi
