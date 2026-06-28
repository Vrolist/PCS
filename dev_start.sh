#!/bin/bash
# pve-cluster-scan 一键开发启动脚本

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "  pve-cluster-scan 开发服务器启动"
echo "========================================="

# 1. 激活虚拟环境
if [ ! -d ".venv" ]; then
    echo "[1/4] 创建虚拟环境..."
    python3.12 -m venv .venv
fi
echo "[1/4] 激活虚拟环境..."
source .venv/bin/activate

# 2. 安装依赖
echo "[2/4] 安装依赖..."
pip install -r requirements.txt -q

# 3. 数据库迁移
echo "[3/4] 执行数据库迁移..."
python manage.py migrate --run-syncdb 2>/dev/null || python manage.py migrate

# 4. 启动开发服务器
echo "[4/4] 启动开发服务器 (http://0.0.0.0:8000)"
echo "========================================="
python manage.py runserver 0.0.0.0:8000
