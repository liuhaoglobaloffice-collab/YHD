#!/bin/bash
# LiuHao AI OS - 健康检查脚本
# 用途：验证全栈健康状态
# 用法：bash scripts/health_check.sh [--wait 60]

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:80}"
WAIT_TIMEOUT=${WAIT_TIMEOUT:-60}

echo "🔍 LiuHao AI OS 健康检查开始..."
echo ""

# 1. 后端 API 健康
echo "📡 检查后端 API ($BACKEND_URL/api/v1/health/ready)..."
if timeout 5 curl -sf "$BACKEND_URL/api/v1/health/ready" > /dev/null 2>&1; then
    echo "  ✅ 后端 API 就绪"
else
    echo "  ⚠️  后端 API 未就绪，等待中..."
    timeout $WAIT_TIMEOUT bash -c "while ! curl -sf '$BACKEND_URL/api/v1/health/ready' > /dev/null 2>&1; do sleep 2; done" && echo "  ✅ 后端 API 就绪" || echo "  ❌ 后端 API 超时"
fi

# 2. 前端 HTTP 状态
echo "📡 检查前端 ($FRONTEND_URL)..."
if timeout 5 curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
    echo "  ✅ 前端 Web 就绪"
else
    echo "  ⚠️  前端 Web 未就绪，等待中..."
    timeout $WAIT_TIMEOUT bash -c "while ! curl -sf '$FRONTEND_URL' > /dev/null 2>&1; do sleep 2; done" && echo "  ✅ 前端 Web 就绪" || echo "  ❌ 前端 Web 超时"
fi

# 3. 容器检查
echo ""
echo "🐳 容器状态："
docker compose ps --services | while read svc; do
    state=$(docker compose ps --filter "service=$svc" --format "{{.State}}" 2>/dev/null || echo "unknown")
    if [ "$state" = "running" ]; then
        echo "  ✅ $svc: $state"
    else
        echo "  ❌ $svc: $state"
    fi
done

# 4. API 文档
echo ""
echo "📖 API 文档可访问："
echo "  - 交互式文档: $BACKEND_URL/docs"
echo "  - ReDoc: $BACKEND_URL/redoc"
echo "  - Prometheus 指标: $BACKEND_URL/metrics"

echo ""
echo "✨ 健康检查完成！"
