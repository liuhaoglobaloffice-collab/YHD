# Enhancement Point 2: Performance & Scalability

## 问题陈述

**当前状态：** 提到了分布式架构，但性能指标不明确

**核心问题：**
```
性能疑问：
├─ 鎏灏能同时服务多少用户？
├─ 单个用户的并发处理能力？
├─ 响应时间SLA是多少？
├─ 高峰期怎么保证性能？
├─ 数据量到TB级怎么办？
├─ 如何应对突发流量？
└─ 如何保证稳定性？
```

---

## 完整解决方案

### 1. 性能指标与SLA承诺

#### 1.1 明确的性能目标

```yaml
系统性能指标（SLA）:

可用性（Availability）:
├─ Uptime SLA
│   ├─ Enterprise: 99.99% (52分钟/年停机)
│   ├─ Business: 99.95% (4.4小时/年停机)
│   ├─ Professional: 99.9% (8.8小时/年停机)
│   └─ Starter: 99.5% (43.8小时/年停机)
│
├─ 计划内维护窗口
│   ├─ 每月第二个周日 02:00-04:00 UTC
│   ├─ 提前14天通知
│   └─ 不计入SLA

响应时间（Latency）:
├─ API响应时间
│   ├─ P50: < 200ms
│   ├─ P95: < 500ms
│   ├─ P99: < 2s
│   └─ Timeout: 30s
│
├─ AI响应时间
│   ├─ Simple Task: < 2s (P95)
│   ├─ Complex Task: < 10s (P95)
│   ├─ Multi-Agent Task: < 30s (P95)
│   └─ Background Task: < 5min
│
├─ Dashboard加载
│   ├─ 首屏: < 1s
│   ├─ 完整页面: < 3s
│   └─ 数据刷新: < 500ms
│
└─ 实时功能
    ├─ WebSocket延迟: < 100ms
    ├─ 推送通知: < 1s
    └─ 状态同步: < 2s

吞吐量（Throughput）:
├─ API请求
│   ├─ Peak: 10,000 req/s
│   ├─ Sustained: 5,000 req/s
│   └─ Burst: 20,000 req/s (5min)
│
├─ AI任务
│   ├─ Concurrent: 1,000 tasks
│   ├─ Daily: 1,000,000 tasks
│   └─ Per User: 100 concurrent tasks
│
└─ 数据处理
    ├─ Data Ingestion: 1GB/s
    ├─ Query Processing: 100,000 queries/s
    └─ Batch Processing: 10TB/hour

容量（Capacity）:
├─ 用户规模
│   ├─ Total Users: 1,000,000+
│   ├─ Concurrent Users: 100,000+
│   ├─ Active Sessions: 50,000+
│   └─ Daily Active Users: 200,000+
│
├─ 数据规模
│   ├─ Total Storage: 100TB+
│   ├─ Hot Data: 10TB
│   ├─ Daily New Data: 100GB
│   └─ Records: 10 billion+
│
└─ AI负载
    ├─ Tokens/Day: 10 billion+
    ├─ Models: 20+ models
    ├─ Embeddings: 100M vectors
    └─ Knowledge Base: 1TB+
```

#### 1.2 SLA保障机制

```python
# liuhao/core/monitoring/sla_monitor.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict
from enum import Enum

class SLAMetric(Enum):
    """SLA指标"""
    UPTIME = "uptime"
    API_LATENCY = "api_latency"
    AI_LATENCY = "ai_latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"

@dataclass
class SLATarget:
    """SLA目标"""
    metric: SLAMetric
    target_value: float
    current_value: float
    unit: str
    status: str  # OK, WARNING, CRITICAL

class SLAMonitor:
    """SLA监控器"""
    
    def __init__(self):
        self.sla_targets = self._initialize_sla_targets()
        self.violation_history: List[SLAViolation] = []
    
    def _initialize_sla_targets(self) -> Dict[SLAMetric, SLATarget]:
        """初始化SLA目标"""
        return {
            SLAMetric.UPTIME: SLATarget(
                metric=SLAMetric.UPTIME,
                target_value=99.99,
                current_value=0.0,
                unit="%",
                status="OK"
            ),
            SLAMetric.API_LATENCY: SLATarget(
                metric=SLAMetric.API_LATENCY,
                target_value=500,  # P95 < 500ms
                current_value=0.0,
                unit="ms",
                status="OK"
            ),
            SLAMetric.AI_LATENCY: SLATarget(
                metric=SLAMetric.AI_LATENCY,
                target_value=2000,  # P95 < 2s
                current_value=0.0,
                unit="ms",
                status="OK"
            ),
            SLAMetric.ERROR_RATE: SLATarget(
                metric=SLAMetric.ERROR_RATE,
                target_value=0.1,  # < 0.1%
                current_value=0.0,
                unit="%",
                status="OK"
            ),
        }
    
    def check_sla(self, metric: SLAMetric, current_value: float):
        """检查SLA"""
        target = self.sla_targets[metric]
        target.current_value = current_value
        
        # 判断是否违反SLA
        violated = False
        if metric == SLAMetric.UPTIME:
            violated = current_value < target.target_value
        elif metric in [SLAMetric.API_LATENCY, SLAMetric.AI_LATENCY]:
            violated = current_value > target.target_value
        elif metric == SLAMetric.ERROR_RATE:
            violated = current_value > target.target_value
        
        if violated:
            target.status = "CRITICAL"
            self._handle_sla_violation(metric, current_value, target.target_value)
        elif current_value >= target.target_value * 0.9:  # 警告阈值
            target.status = "WARNING"
            self._send_warning(metric, current_value, target.target_value)
        else:
            target.status = "OK"
    
    def _handle_sla_violation(self, metric: SLAMetric, current: float, target: float):
        """处理SLA违规"""
        violation = SLAViolation(
            metric=metric,
            timestamp=datetime.now(),
            current_value=current,
            target_value=target,
            severity="CRITICAL"
        )
        
        self.violation_history.append(violation)
        
        # 1. 立即告警
        self._send_alert(violation)
        
        # 2. 触发自动修复
        self._trigger_auto_remediation(metric)
        
        # 3. 记录事件
        self._log_incident(violation)
        
        # 4. 通知客户（如果严重）
        if self._should_notify_customers(violation):
            self._notify_affected_customers(violation)
    
    def _trigger_auto_remediation(self, metric: SLAMetric):
        """触发自动修复"""
        if metric == SLAMetric.API_LATENCY:
            # 增加服务实例
            self._scale_out_api_servers()
        elif metric == SLAMetric.AI_LATENCY:
            # 切换到更快的模型或增加容量
            self._scale_out_ai_workers()
        elif metric == SLAMetric.ERROR_RATE:
            # 重启有问题的服务
            self._restart_unhealthy_services()
    
    def generate_sla_report(self, start_date: datetime, end_date: datetime):
        """生成SLA报告"""
        period_hours = (end_date - start_date).total_seconds() / 3600
        
        # 计算实际可用时间
        downtime_minutes = self._calculate_downtime(start_date, end_date)
        uptime_percentage = ((period_hours * 60 - downtime_minutes) / (period_hours * 60)) * 100
        
        # 获取延迟统计
        api_latency_p95 = self._get_percentile_latency("api", 95, start_date, end_date)
        ai_latency_p95 = self._get_percentile_latency("ai", 95, start_date, end_date)
        
        # 计算错误率
        error_rate = self._calculate_error_rate(start_date, end_date)
        
        return {
            "period": f"{start_date} to {end_date}",
            "uptime_percentage": uptime_percentage,
            "downtime_minutes": downtime_minutes,
            "api_latency_p95_ms": api_latency_p95,
            "ai_latency_p95_ms": ai_latency_p95,
            "error_rate_percentage": error_rate,
            "sla_targets": {
                "uptime": 99.99,
                "api_latency_p95": 500,
                "ai_latency_p95": 2000,
                "error_rate": 0.1,
            },
            "sla_status": {
                "uptime": "MET" if uptime_percentage >= 99.99 else "MISSED",
                "api_latency": "MET" if api_latency_p95 <= 500 else "MISSED",
                "ai_latency": "MET" if ai_latency_p95 <= 2000 else "MISSED",
                "error_rate": "MET" if error_rate <= 0.1 else "MISSED",
            },
            "violations": [v.to_dict() for v in self.violation_history 
                         if start_date <= v.timestamp <= end_date]
        }
```

---

### 2. 自动扩缩容策略

#### 2.1 水平扩展（Horizontal Scaling）

```yaml
自动扩缩容规则:

API服务器扩缩容:
├─ 扩容触发条件
│   ├─ CPU使用率 > 70% (持续5分钟)
│   ├─ 内存使用率 > 80% (持续5分钟)
│   ├─ 请求队列 > 1000
│   ├─ P95延迟 > 1000ms (持续5分钟)
│   └─ 错误率 > 5% (持续2分钟)
│
├─ 扩容策略
│   ├─ 每次增加：当前实例数 * 50%
│   ├─ 最小增量：2个实例
│   ├─ 最大实例数：100
│   ├─ 冷却时间：5分钟
│   └─ 预热时间：2分钟
│
├─ 缩容触发条件
│   ├─ CPU使用率 < 30% (持续20分钟)
│   ├─ 内存使用率 < 40% (持续20分钟)
│   ├─ 请求量低于平时50% (持续30分钟)
│   └─ 非高峰时段
│
└─ 缩容策略
    ├─ 每次减少：当前实例数 * 25%
    ├─ 最小实例数：4（保证高可用）
    ├─ 冷却时间：15分钟
    └─ 优雅关闭：等待现有请求完成

AI Worker扩缩容:
├─ 扩容触发条件
│   ├─ AI任务队列 > 100
│   ├─ 平均等待时间 > 10s
│   ├─ GPU使用率 > 85%
│   └─ Token处理速度下降
│
├─ 扩容策略
│   ├─ 根据模型类型独立扩展
│   ├─ GPT-4: 最多10个worker
│   ├─ Claude: 最多10个worker
│   ├─ 轻量模型: 最多20个worker
│   └─ 使用Spot实例降低成本
│
└─ 缩容策略
    ├─ 任务队列 < 10 (持续15分钟)
    ├─ 保留最小2个worker (高可用)
    └─ 优雅关闭：完成当前任务

数据库扩缩容:
├─ 读副本自动扩展
│   ├─ 读操作QPS > 10,000
│   ├─ 读延迟 > 100ms (P95)
│   ├─ 自动增加只读副本
│   └─ 最多8个读副本
│
├─ 连接池动态调整
│   ├─ 根据实际连接数调整
│   ├─ Min: 10, Max: 200
│   └─ 空闲连接自动回收
│
└─ 分片策略
    ├─ 单表 > 100M行 → 考虑分片
    ├─ 按tenant_id分片
    └─ 按时间分片（时序数据）
```

#### 2.2 Kubernetes配置

```yaml
# k8s/api-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: liuhao-api
  namespace: production
spec:
  replicas: 4  # 最小副本数
  selector:
    matchLabels:
      app: liuhao-api
  template:
    metadata:
      labels:
        app: liuhao-api
    spec:
      containers:
      - name: api
        image: liuhao/api:latest
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        env:
        - name: MAX_WORKERS
          value: "4"
        - name: WORKER_TIMEOUT
          value: "30"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: liuhao-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: liuhao-api
  minReplicas: 4
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25
        periodSeconds: 60
      selectPolicy: Min
```

---

### 3. 性能优化策略

#### 3.1 多层缓存架构

```yaml
缓存层次:

L1: Application Cache (应用层缓存)
├─ 位置: 应用内存
├─ 技术: Python dict / LRU Cache
├─ 大小: 500MB per instance
├─ TTL: 5-60秒
├─ 用途:
│   ├─ 热点数据
│   ├─ 计算结果
│   └─ 频繁访问的对象
└─ 命中率目标: > 70%

L2: Distributed Cache (分布式缓存)
├─ 位置: Redis Cluster
├─ 大小: 100GB
├─ TTL: 1分钟-24小时
├─ 用途:
│   ├─ Session数据
│   ├─ API响应缓存
│   ├─ 用户配置
│   ├─ 权限信息
│   └─ 频繁查询结果
├─ 命中率目标: > 85%
└─ 高可用: 主从复制 + Sentinel

L3: Database Query Cache (数据库查询缓存)
├─ 位置: PostgreSQL Query Cache
├─ 大小: 16GB
├─ TTL: 自动失效
├─ 用途:
│   ├─ 复杂查询结果
│   ├─ 聚合计算
│   └─ Join结果
└─ 命中率目标: > 60%

L4: CDN Cache (CDN缓存)
├─ 位置: Cloudflare / AWS CloudFront
├─ 大小: 无限
├─ TTL: 1小时-30天
├─ 用途:
│   ├─ 静态资源
│   ├─ API响应（GET）
│   ├─ 图片/视频
│   └─ 前端资源
└─ 命中率目标: > 95%

L5: Browser Cache (浏览器缓存)
├─ 位置: 用户浏览器
├─ TTL: 根据资源类型
├─ 用途:
│   ├─ 静态资源
│   ├─ LocalStorage数据
│   └─ IndexedDB数据
└─ 命中率目标: > 90%
```

#### 3.2 缓存实现

```python
# liuhao/core/cache/multi_level_cache.py

from typing import Optional, Any, Callable
from functools import wraps
import hashlib
import json
import redis
from cachetools import LRUCache

class MultiLevelCache:
    """多层缓存"""
    
    def __init__(self):
        # L1: 应用层缓存
        self.l1_cache = LRUCache(maxsize=10000)
        
        # L2: Redis缓存
        self.redis_client = redis.Redis(
            host='redis-cluster',
            port=6379,
            decode_responses=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 1. 尝试L1缓存
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # 2. 尝试L2缓存（Redis）
        value = self.redis_client.get(key)
        if value:
            # 反序列化
            data = json.loads(value)
            # 回填到L1
            self.l1_cache[key] = data
            return data
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
        # 1. 写入L1
        self.l1_cache[key] = value
        
        # 2. 写入L2（异步）
        serialized = json.dumps(value)
        self.redis_client.setex(key, ttl, serialized)
    
    def delete(self, key: str):
        """删除缓存"""
        # 删除L1
        if key in self.l1_cache:
            del self.l1_cache[key]
        
        # 删除L2
        self.redis_client.delete(key)
    
    def clear_pattern(self, pattern: str):
        """清除匹配的缓存"""
        # 清除L1（全部）
        self.l1_cache.clear()
        
        # 清除L2（匹配pattern）
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)

def cached(ttl: int = 300, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = f"{key_prefix}:{func.__name__}:"
            cache_key += hashlib.md5(
                json.dumps((args, kwargs), sort_keys=True).encode()
            ).hexdigest()
            
            # 尝试从缓存获取
            cache = MultiLevelCache()
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator

# 使用示例
@cached(ttl=60, key_prefix="user")
def get_user_profile(user_id: str):
    """获取用户资料（缓存60秒）"""
    # 实际数据库查询
    return db.query(User).filter(User.id == user_id).first()
```

#### 3.3 数据库优化

```yaml
数据库性能优化:

索引优化:
├─ 单列索引
│   ├─ Primary Key: (id)
│   ├─ Foreign Key: (tenant_id, user_id, etc.)
│   └─ 常用查询字段: (email, created_at, status)
│
├─ 复合索引
│   ├─ (tenant_id, created_at) - 租户时间查询
│   ├─ (tenant_id, user_id, status) - 用户状态查询
│   └─ (tenant_id, department_id, team_id) - 组织架构查询
│
├─ 部分索引
│   ├─ WHERE status = 'active' - 只索引活跃记录
│   └─ WHERE deleted_at IS NULL - 只索引未删除记录
│
└─ 全文索引
    ├─ GIN索引（PostgreSQL）
    └─ 用于文本搜索

查询优化:
├─ 避免N+1问题
│   ├─ 使用JOIN或预加载
│   ├─ SQLAlchemy: .options(joinedload())
│   └─ 批量查询替代循环查询
│
├─ 分页优化
│   ├─ 使用游标分页（cursor-based）
│   ├─ 避免OFFSET大值
│   └─ 使用索引字段排序
│
├─ 聚合优化
│   ├─ 使用物化视图
│   ├─ 定期更新统计数据
│   └─ 使用预计算表
│
└─ 慢查询优化
    ├─ 监控慢查询日志
    ├─ EXPLAIN ANALYZE分析
    ├─ 优化查询计划
    └─ 添加必要索引

连接池优化:
├─ 大小配置
│   ├─ Min Pool Size: 10
│   ├─ Max Pool Size: 100
│   ├─ Max Overflow: 50
│   └─ Pool Timeout: 30s
│
├─ 连接复用
│   ├─ 使用长连接
│   ├─ 连接预热
│   └─ 连接健康检查
│
└─ 连接泄露防护
    ├─ 自动回收超时连接
    ├─ 监控连接使用情况
    └─ 告警机制

读写分离:
├─ 主库（Master）
│   ├─ 所有写操作
│   ├─ 强一致性读
│   └─ 事务操作
│
└─ 从库（Replicas）
    ├─ 所有只读查询
    ├─ 分析查询
    ├─ 负载均衡
    └─ 最终一致性
```

---

### 4. 负载测试与压力测试

#### 4.1 测试策略

```yaml
性能测试类型:

负载测试（Load Testing）:
├─ 目标: 验证系统在预期负载下的性能
├─ 场景:
│   ├─ 1,000 并发用户
│   ├─ 持续1小时
│   ├─ 混合操作（70%读, 30%写）
│   └─ 真实用户行为模拟
├─ 验收标准:
│   ├─ P95延迟 < 500ms
│   ├─ 错误率 < 0.1%
│   └─ 吞吐量 > 5,000 req/s

压力测试（Stress Testing）:
├─ 目标: 找到系统的极限
├─ 场景:
│   ├─ 逐步增加负载
│   ├─ 从1,000到100,000用户
│   ├─ 每5分钟增加20%
│   └─ 直到系统崩溃
├─ 验收标准:
│   ├─ 找到最大容量
│   ├─ 观察降级行为
│   └─ 验证错误处理

峰值测试（Spike Testing）:
├─ 目标: 验证突发流量处理能力
├─ 场景:
│   ├─ 正常负载: 1,000用户
│   ├─ 突然增加到50,000用户
│   ├─ 持续10分钟
│   └─ 恢复到正常负载
├─ 验收标准:
│   ├─ 5分钟内完成扩容
│   ├─ 峰值期间可用性 > 99%
│   └─ 恢复后系统正常

浸泡测试（Soak Testing）:
├─ 目标: 验证长期运行稳定性
├─ 场景:
│   ├─ 中等负载
│   ├─ 持续运行7天
│   └─ 监控资源泄漏
├─ 验收标准:
│   ├─ 无内存泄漏
│   ├─ 无性能退化
│   └─ 系统稳定运行
```

#### 4.2 Locust测试脚本

```python
# tests/performance/locustfile.py

from locust import HttpUser, task, between
import random
import json

class LiuHaoUser(HttpUser):
    """鎏灏用户行为模拟"""
    
    wait_time = between(1, 5)  # 用户操作间隔1-5秒
    
    def on_start(self):
        """用户登录"""
        response = self.client.post("/api/auth/login", json={
            "email": f"user{random.randint(1, 10000)}@example.com",
            "password": "test123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(10)  # 权重10
    def view_dashboard(self):
        """查看仪表板（最常见操作）"""
        self.client.get(
            "/api/dashboard",
            headers=self.headers,
            name="/api/dashboard"
        )
    
    @task(5)
    def list_customers(self):
        """查看客户列表"""
        self.client.get(
            "/api/customers?page=1&limit=20",
            headers=self.headers,
            name="/api/customers [list]"
        )
    
    @task(3)
    def create_customer(self):
        """创建客户"""
        self.client.post(
            "/api/customers",
            headers=self.headers,
            json={
                "name": f"Customer {random.randint(1, 100000)}",
                "email": f"customer{random.randint(1, 100000)}@example.com",
                "industry": "Manufacturing"
            },
            name="/api/customers [create]"
        )
    
    @task(7)
    def ask_ai(self):
        """询问AI（核心功能）"""
        questions = [
            "分析一下这个月的销售情况",
            "帮我写一封客户跟进邮件",
            "哪些客户最近没有联系",
            "本季度的营收预测",
            "竞争对手最近有什么动态"
        ]
        
        self.client.post(
            "/api/ai/ask",
            headers=self.headers,
            json={
                "question": random.choice(questions),
                "context": {"tenant_id": self.token}
            },
            name="/api/ai/ask",
            timeout=30  # AI请求可能较慢
        )
    
    @task(2)
    def generate_report(self):
        """生成报告"""
        self.client.post(
            "/api/reports/generate",
            headers=self.headers,
            json={
                "type": "sales_summary",
                "period": "last_month"
            },
            name="/api/reports/generate"
        )
    
    @task(1)
    def export_data(self):
        """导出数据（较少但重要）"""
        self.client.get(
            "/api/customers/export?format=csv",
            headers=self.headers,
            name="/api/customers [export]"
        )

# 运行测试:
# locust -f tests/performance/locustfile.py --host=https://api.liuhao.ai

# 压力测试:
# locust -f locustfile.py --headless --users 10000 --spawn-rate 100 -t 1h
```

---

## 总结

**性能优化的关键要点：**

1. **明确SLA**：量化的性能目标和承诺
2. **自动扩缩容**：应对流量波动，保证性能和成本平衡
3. **多层缓存**：减少数据库压力，提升响应速度
4. **数据库优化**：索引、查询、连接池、读写分离
5. **持续测试**：定期压力测试，提前发现瓶颈

**实施优先级：**
- P0: 基本性能监控、缓存、数据库索引
- P1: 自动扩缩容、SLA监控
- P2: 多层缓存优化、读写分离
- P3: 持续性能测试、深度优化

---

## 下一步

完善点3：[用户侧可观测性与调试](./03_USER_OBSERVABILITY.md)
