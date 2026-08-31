# LiuHao AI OS - 生产部署最佳实践

## 📋 部署前清单

### 1. **环境变量安全**
- [ ] `.env` 文件已创建且 `.gitignore` 中排除
- [ ] `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY` 均为 ≥32 位随机字符串
  - 生成方法：`python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] `POSTGRES_PASSWORD` 为强密码（≥16 位，含大小写+数字+特殊字符）
- [ ] 敏感变量不存在于 docker-compose.yml、Dockerfile、代码中

### 2. **Docker 镜像优化**
- [x] 后端 Dockerfile 使用多阶段构建（builder → runtime）
- [x] 前端 Dockerfile 使用多阶段构建（build → nginx）
- [x] `.dockerignore` 包含所有非必需文件（node_modules, .env, 测试, 文档）
- [ ] 本地构建验证：`docker build -t liuhao-ai-os-backend:latest .`

### 3. **容器健康检查**
- [x] 后端 Dockerfile 包含 HEALTHCHECK 指令
- [x] 数据库 docker-compose 配置了 `pg_isready` 检查
- [x] 前端 nginx 配置了 HTTP 200 检查
- [ ] 验证：`docker compose ps` 显示 healthy 状态

### 4. **网络与端口**
- [ ] 80（前端）、8000（后端）、5432（数据库）未被其他服务占用
- [ ] 防火墙允许必需的入站端口
- [ ] 反向代理配置正确（nginx.conf 已审查）

### 5. **数据库准备**
- [ ] PostgreSQL 16 已安装或容器镜像可用
- [ ] 数据卷挂载点 `liuhao_pgdata` 可写
- [ ] 数据库初始化脚本（若需要）已准备

### 6. **LLM 提供商配置**
- [ ] 选定 LLM 提供商（ollama / openai / mock）
- [ ] 若选 ollama：宿主机已安装 Ollama，模型已下载
- [ ] 若选 openai：API Key 已配置到 `.env`
- [ ] 若选 mock：仅用于演示，功能受限

### 7. **日志与监控**
- [ ] 容器日志重定向配置（可选）
- [ ] Prometheus 指标端点可访问
- [ ] 审计日志落库成功

### 8. **备份与恢复**
- [ ] 数据卷备份策略已制定
- [ ] 恢复脚本已测试
- [ ] `.env` 和 docker-compose.yml 已备份到安全位置

---

## 🚀 部署步骤

### 快速启动（推荐）

```bash
# 1. 检查部署准备
python scripts/pre_deploy_check.py

# 2. 启动全栈
docker compose up -d --build

# 3. 等待服务就绪
bash scripts/health_check.sh

# 4. 验证功能
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:80
```

### 分步启动（用于调试）

```bash
# 仅启动数据库
docker compose up -d database
docker compose logs database

# 启动后端
docker compose up -d backend
docker compose logs backend

# 启动前端
docker compose up -d frontend
docker compose logs frontend
```

---

## 🔧 常见问题

### 后端启动失败（exited with code 1）
```bash
# 查看日志
docker compose logs backend

# 常见原因：
# 1. 数据库连接失败 → 检查 DATABASE_URL、POSTGRES_PASSWORD
# 2. 环境变量缺失 → 检查 .env 中的 SECRET_KEY、JWT_SECRET_KEY
# 3. 端口被占用 → lsof -i :8000 或 netstat -tulpn | grep 8000
# 4. 权限问题 → docker compose exec backend ls -la src/
```

### 前端 nginx 返回 502 Bad Gateway
```bash
# 问题：前端 nginx 无法连接到后端
# 解决：
# 1. 检查后端是否运行：docker compose ps backend
# 2. 验证 nginx.conf 中的后端地址（应该是 backend:8000）
# 3. 查看 frontend 日志：docker compose logs frontend
```

### 数据库连接异常
```bash
# 验证数据库健康状态
docker compose exec database pg_isready -U liuhao_user -d liuhao_ai_os

# 进入 psql 交互环境
docker compose exec database psql -U liuhao_user -d liuhao_ai_os

# 检查卷挂载
docker inspect liuhao-database --format='{{json .Mounts}}'
```

### Ollama 无法连接
```bash
# Docker 容器访问宿主机用 host.docker.internal
# 验证连接：
docker compose exec backend curl -i http://host.docker.internal:11434/api/tags

# 若不可达，尝试：
# 1. 确认宿主机 Ollama 运行：ollama list
# 2. Ollama 监听地址：OLLAMA_HOST=0.0.0.0:11434 ollama serve
# 3. 容器内 DNS：docker compose exec backend getent hosts host.docker.internal
```

---

## 📊 生产监控

### 访问关键端点

| 端点 | 用途 | 示例 |
|---|---|---|
| `/api/v1/health/ready` | 容器就绪探针 | `curl http://localhost:8000/api/v1/health/ready` |
| `/metrics` | Prometheus 指标 | `curl http://localhost:8000/metrics` |
| `/docs` | Swagger UI | `http://localhost:8000/docs` |
| `/redoc` | ReDoc 文档 | `http://localhost:8000/redoc` |

### 容器资源监控

```bash
# 实时监控
docker stats liuhao-backend liuhao-frontend liuhao-database

# 查看历史消耗
docker compose exec backend cat /proc/self/status | grep VmRSS
```

---

## 🔐 安全加固

### 1. 网络隔离
```bash
# 创建内部网络（生产环境）
docker network create --driver bridge liuhao-internal

# 在 docker-compose.yml 中配置
networks:
  liuhao-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.19.0.0/16
```

### 2. 镜像扫描
```bash
# 扫描后端镜像（Trivy）
trivy image liuhao-ai-os-backend:latest

# 或使用 Docker Scout
docker scout cves liuhao-ai-os-backend:latest
```

### 3. 密钥轮换
```bash
# 生成新的 SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# 更新 .env，重启容器
docker compose up -d --build
```

### 4. 日志审计
```bash
# 查看容器启动/停止事件
docker events --filter type=container

# 导出审计日志
docker compose exec backend tail -f /var/log/audit.log  # 若有审计模块
```

---

## 🛠️ 维护操作

### 备份数据库

```bash
# 完整备份
docker compose exec database pg_dump -U liuhao_user liuhao_ai_os > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复
docker compose exec -T database psql -U liuhao_user liuhao_ai_os < backup.sql
```

### 迁移数据库

```bash
# 导出卷数据
docker run --rm -v liuhao-ai-os_liuhao_pgdata:/data -v $(pwd):/backup alpine tar czf /backup/pgdata.tar.gz /data

# 导入到新卷
docker run --rm -v liuhao-ai-os_liuhao_pgdata:/data -v $(pwd):/backup alpine tar xzf /backup/pgdata.tar.gz -C /
```

### 更新镜像

```bash
# 重新构建（若修改了代码）
docker compose build --no-cache

# 应用更新
docker compose up -d

# 验证
docker compose ps
```

---

## 📈 扩展建议

### 1. 负载均衡
- 使用 docker-compose 的 `replicas` 或 Swarm/K8s
- 配置 nginx upstream（多后端实例）

### 2. 持久化存储
- 生产环境推荐外部 PostgreSQL（RDS / 阿里 RDS）
- 卷备份策略（定时快照、异地冷备）

### 3. CI/CD 集成
- GitHub Actions / GitLab CI 自动化构建与推送镜像
- 部署前自动运行 tests 和 pre_deploy_check.py

### 4. 容器编排
- 考虑迁移到 Docker Swarm 或 Kubernetes
- 自动故障转移、滚动更新、资源限制

---

## 📞 故障排查

### 查看实时日志

```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f database

# 最近 100 行
docker compose logs --tail 100 backend
```

### 进入容器调试

```bash
# bash
docker compose exec backend bash

# Python 交互环境
docker compose exec backend python -c "import src; print(src.__file__)"

# 数据库查询
docker compose exec database psql -U liuhao_user -d liuhao_ai_os -c "SELECT version();"
```

### 重启服务

```bash
# 完全重启
docker compose restart

# 特定服务
docker compose restart backend

# 冷启动（杀死并移除）
docker compose down
docker compose up -d
```

---

## ✅ 部署后验证

运行冒烟测试确保全栈可用：

```bash
python scripts/verify_api_smoke.py \
  --username admin \
  --password yourpassword \
  --base http://localhost:8000
```

期望结果：
- 所有 28 个 API 通过
- 返回码 0（成功）

---

**最后更新**：2026-08-30  
**维护者**：LiuHao AI Team
