#!/bin/bash
# pve-cluster-scan 前端一键启动脚本

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR/frontend"

echo "========================================="
echo "  pve-cluster-scan 前端开发服务器启动"
echo "========================================="

# 1. 安装依赖
echo "[1/2] 安装依赖..."
npm install

# 2. 启动开发服务器
echo "[2/2] 启动开发服务器 (http://localhost:5173)"
echo "========================================="
npm run dev
