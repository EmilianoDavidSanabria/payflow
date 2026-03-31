#!/bin/sh
set -e

cd /app/payflow

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn payflow.wsgi:application \
  --bind 0.0.0.0:${PORT:-8080} \
  --access-logfile - \
  --error-logfile -