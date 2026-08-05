# ============================================================
# Stage 1: 前端构建
# ============================================================
FROM node:24-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
RUN npx vite build

# ============================================================
# Stage 2: Python 依赖
# ============================================================
FROM python:3.12-slim AS backend-deps
WORKDIR /app

# 安装编译依赖（python-ldap 需要 libldap2-dev 和 libsasl2-dev）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2-dev libsasl2-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 3: 最终镜像
# ============================================================
FROM python:3.12-slim

# 系统依赖（包含 LDAP 开发库以支持 python-ldap）
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 curl \
    libldap2-dev libsasl2-dev && \
    rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖
COPY --from=backend-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-deps /usr/local/bin /usr/local/bin

# 工作目录
WORKDIR /app

# 复制后端代码
COPY . .

# 启动脚本
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 复制前端构建产物
COPY --from=frontend-build /app/static/frontend/ /app/static/frontend/

# 数据目录（SQLite + media）
RUN mkdir -p /app/data /app/media
VOLUME /app/data /app/media

# 环境变量
ENV DB_PATH=/app/data/db.sqlite3
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8066

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8066/api/auth/login/ || exit 1

# 启动：entrypoint 负责 migrate + 静态文件 + 超级管理员 + uvicorn
CMD ["/app/entrypoint.sh"]
