# S6 生产部署 - 后端镜像（多阶段构建 + 最小化层）
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 分层缓存：依赖层单独打包
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 运行时最小依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 pip 用户包
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=10s \
    CMD curl -f http://localhost:8000/api/v1/health/ready || exit 1

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]