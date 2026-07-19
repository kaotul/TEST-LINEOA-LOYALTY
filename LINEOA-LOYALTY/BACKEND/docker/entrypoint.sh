#!/bin/sh
set -e

echo "[entrypoint] waiting for postgres at ${DB_HOST:-db}:${DB_PORT:-5432} ..."
python - << 'PYEOF'
import os
import socket
import time

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))

for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("postgres not reachable, giving up")
PYEOF
echo "[entrypoint] postgres is up"

# กรณีนี้ยังไม่ commit ไฟล์ migration ล่วงหน้า จึงสร้างและรันตอน container start
# (สำหรับทีมโปรดักชันจริง แนะนำให้ generate migrations แล้ว commit เข้า repo แทน)
python manage.py makemigrations customers points pos line_integration --noinput
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
