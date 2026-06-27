#!/bin/sh
set -e

python3 - <<'PYEOF'
import os
import sqlalchemy as sa

url = os.environ.get("DATABASE_URL")
if url:
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        has_version_table = conn.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'alembic_version')"
        )).scalar()
        has_users_table = conn.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'users')"
        )).scalar()

        if not has_version_table and has_users_table:
            conn.execute(sa.text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(sa.text("INSERT INTO alembic_version (version_num) VALUES ('d0d40b4db7ac')"))
            conn.commit()
            print("Stamped pre-existing schema at d0d40b4db7ac")
PYEOF

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
