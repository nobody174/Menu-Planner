#!/bin/sh
set -e

# This container starts as root specifically to fix ownership of /app/data,
# since a Railway persistent volume mounted at runtime brings its own
# ownership (typically root) that overrides whatever the Dockerfile's
# build-time `chown -R appuser:appuser /app` set - without this, appuser
# gets "Permission denied" trying to write into the volume even though the
# image was built correctly. logs/ gets the same treatment for consistency,
# though it isn't volume-backed today.
chown -R appuser:appuser /app/data /app/logs 2>/dev/null || true

# Restore seed data files into the (possibly empty, if this is a fresh
# Railway persistent volume) /app/data directory. Only copies files that
# don't already exist there, so real data from a previous boot is never
# overwritten - this only fills in what's genuinely missing.
if [ -d /app/data-seed ]; then
    cp -rn /app/data-seed/. /app/data/ 2>/dev/null || true
    chown -R appuser:appuser /app/data
fi

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

# Drop from root to appuser for the actual app process. gosu execs gunicorn
# directly (replacing this shell, same as the old `exec gunicorn ...` did)
# so it still runs as PID 1's real child and receives SIGTERM correctly on
# Railway restarts/redeploys - `su` would interpose an extra shell layer and
# can swallow signals, which is why gosu is used here instead.
exec gosu appuser gunicorn \
    --bind 0.0.0.0:${PORT:-5000} \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    deployment.flask_app:app
