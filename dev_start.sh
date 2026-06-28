#!/bin/bash
# pve-cluster-scan 一键开发启动脚本
# 同时启动 Django 后端 + Vite 前端（django-vite 集成模式）

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "  pve-cluster-scan  开发服务器启动"
echo "========================================="

# 1. 激活虚拟环境
if [ ! -d ".venv" ]; then
    echo "[1/5] 创建虚拟环境..."
    python3.12 -m venv .venv
fi
echo "[1/5] 激活虚拟环境..."
source .venv/bin/activate

# 2. 安装后端依赖
echo "[2/5] 安装后端依赖..."
pip install -r requirements.txt -q

# 3. 数据库迁移
echo "[3/5] 执行数据库迁移..."
python manage.py migrate

# 4. 安装前端依赖并构建
echo "[4/5] 安装前端依赖..."
cd frontend && npm install && cd ..

# 5. 启动服务（前台：Django + 后台：Vite）
echo "[5/5] 启动服务..."
echo ""
echo "   Django 后端:  http://0.0.0.0:8000"
echo "   Vite  前端:   http://localhost:5173"
echo "========================================="

# 后台启动 Vite 开发服务器
cd frontend && npm run dev &
VITE_PID=$!
cd "$PROJECT_DIR"

# 前台启动 Django
python manage.py runserver 0.0.0.0:8000

# 退出时关闭 Vite
kill $VITE_PID 2>/dev/null
