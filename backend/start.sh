#!/bin/sh
set -e

cd /app

# Run migrations if alembic is available
if command -v alembic >/dev/null 2>&1; then
    alembic upgrade head 2>/dev/null || echo "No migrations to run"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --timeout-keep-alive 60
