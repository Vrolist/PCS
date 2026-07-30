#!/bin/bash
# pve-cluster-scan 一键启动脚本
# 构建前端 + Django 单服务模式（无 Vite，流式直出）

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "  pve-cluster-scan  服务启动"
echo "========================================="

# 1. 激活虚拟环境
if [ ! -d ".venv" ]; then
    echo "[1/6] 创建虚拟环境..."
    python3.12 -m venv .venv
fi
echo "[1/6] 激活虚拟环境..."
source .venv/bin/activate

# 2. 安装后端依赖
echo "[2/6] 安装后端依赖..."
pip install -r requirements.txt -q

# 3. 数据库迁移
echo "[3/6] 执行数据库迁移..."
python manage.py migrate

# 3.5 创建超级管理员
echo "[3.5/6] 检查管理员账户..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='pcs').exists():
    User.objects.create_superuser('pcs', '1121031509@qq.com', '123456')
    print('  ✓ 管理员账户已创建: pcs')
else:
    print('  ✓ 管理员账户已存在: pcs')
"

# 4. 安装前端依赖并构建
echo "[4/6] 安装前端依赖..."
cd frontend && npm install
echo "[4/6] 构建前端..."
npx vite build
cd "$PROJECT_DIR"

# 5. 收集静态文件
echo "[5/6] 收集静态文件..."
python manage.py collectstatic --noinput 2>/dev/null || true

# 6. 启动 Django（单服务模式，无 Vite）
echo "[6/6] 启动服务..."
echo ""
echo "   访问地址:  http://<本机IP>:8066"
echo "========================================="

source .venv/bin/activate && uvicorn config.asgi:application --host 0.0.0.0 --port 8066 --reload
