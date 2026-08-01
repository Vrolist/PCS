#!/usr/bin/env bash
set -e

SUPERUSER_USERNAME="${SUPERUSER_USERNAME:-pcs}"
SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-1121031509@qq.com}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-123456}"

echo "[1/4] 执行数据库迁移..."
RETRIES=0
until python manage.py migrate --noinput; do
    RETRIES=$((RETRIES + 1))
    if [ "$RETRIES" -ge 30 ]; then
        echo "  ✗ 数据库迁移失败，已重试 30 次，退出"
        exit 1
    fi
    echo "  … 数据库未就绪，2 秒后重试 ($RETRIES/30)"
    sleep 2
done

echo "[2/4] 收集静态文件..."
python manage.py collectstatic --noinput

echo "[3/4] 检查超级管理员账户..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
U = get_user_model()
username = os.environ.get('SUPERUSER_USERNAME', 'pcs')
email = os.environ.get('SUPERUSER_EMAIL', '1121031509@qq.com')
password = os.environ.get('SUPERUSER_PASSWORD', '123456')
if not U.objects.filter(username=username).exists():
    U.objects.create_superuser(username, email, password)
    print(f'  ✓ 超级管理员已创建: {username}')
else:
    print(f'  ✓ 超级管理员已存在: {username}')
"

echo "[4/4] 启动 uvicorn..."
exec uvicorn config.asgi:application --host 0.0.0.0 --port 8066 --workers 2
