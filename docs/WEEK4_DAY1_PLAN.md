# Week 4 Day 1: Ollama Provider 实现

**日期**: 2026-08-24
**任务**: 实现 Ollama 本地 LLM 集成

---

## 📋 任务清单

### 1. 安装依赖 (10分钟)
- [ ] 安装 ollama Python 客户端: `pip install ollama`
- [ ] 更新 requirements.txt
- [ ] 验证安装

### 2. 实现 OllamaProvider (30分钟)
- [ ] 在 `src/ai/providers.py` 中实现 `OllamaProvider` 类
- [ ] 继承 `BaseProvider`
- [ ] 实现 `complete()` 方法
- [ ] 实现模型加载检查
- [ ] 实现流式响应（如果支持）

### 3. 配置管理 (15分钟)
- [ ] 更新 `src/core/config.py` 添加 Ollama 配置
- [ ] 环境变量：`OLLAMA_HOST`, `OLLAMA_DEFAULT_MODEL`
- [ ] 默认配置：localhost:11434, qwen2.5:7b

### 4. 单元测试 (20分钟)
- [ ] 创建 `tests/ai/test_ollama_provider.py`
- [ ] 测试 Provider 初始化
- [ ] 测试 complete() 方法（mock）
- [ ] 测试健康检查
- [ ] 测试错误处理

### 5. 集成测试 (15分钟)
- [ ] 创建 Ollama 集成脚本 `scripts/test_ollama.py`
- [ ] 测试基本对话
- [ ] 测试不同温度参数
- [ ] 性能基准测试

---

## 🎯 成功标准

1. ✅ OllamaProvider 实现完整
2. ✅ 单元测试通过率 100%
3. ✅ 集成测试脚本可运行（即使 Ollama 未安装也能优雅降级）
4. ✅ 文档完整（配置说明、使用示例）

---

## 📝 实现细节

### OllamaProvider API 映射

```python
# Ollama API 调用示例
import ollama

response = ollama.chat(
    model='qwen2.5:7b',
    messages=[
        {'role': 'user', 'content': 'Hello'}
    ]
)
```

### 配置示例

```yaml
# .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_DEFAULT_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=60
```

---

## ⏰ 预计时间

- 总计: 90分钟
- 开始: 2026-08-24 06:50
- 预计完成: 2026-08-24 08:20

---

## 📊 交付物

1. `src/ai/providers.py` - 新增 OllamaProvider 类
2. `src/core/config.py` - 新增 Ollama 配置
3. `tests/ai/test_ollama_provider.py` - 单元测试
4. `scripts/test_ollama.py` - 集成测试脚本
5. `requirements.txt` - 更新依赖
6. `docs/WEEK4_DAY1_REPORT.md` - 完成报告
