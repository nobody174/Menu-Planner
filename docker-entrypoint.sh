#!/bin/sh
set -e

alembic upgrade head

exec gunicorn \
    --bind 0.0.0.0:${PORT:-5000} \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    pi-deployment.flask_app:app
