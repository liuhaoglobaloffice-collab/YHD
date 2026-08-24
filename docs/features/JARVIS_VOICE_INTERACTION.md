# 🎤 贾维斯语音交互系统

**状态**: ✅ 核心功能已实现

---

## 📋 功能概述

贾维斯级语音交互系统，支持：
- ✅ 多语言唤醒词检测（"嘿鎏灏", "Hey LiuHao", "Jarvis" 等）
- ✅ 状态机管理（待机→监听→处理→响应）
- ✅ 语音识别（Whisper API）
- ✅ 文字转语音（OpenAI TTS）
- ✅ REST API 端点

---

## 🏗️ 架构

```
用户语音输入
    ↓
[唤醒词检测] → 状态: IDLE → LISTENING
    ↓
[语音识别 ASR] → Whisper API
    ↓
[命令处理] → 状态: PROCESSING
    ↓
[生成回复] → AI/规则引擎
    ↓
[语音合成 TTS] → OpenAI TTS → 状态: RESPONDING
    ↓
返回音频 → 状态: IDLE
```

---

## 📁 文件结构

```
src/jarvis/
├── __init__.py              # 模块初始化
├── service.py               # 主服务类
├── state_machine.py         # 状态机管理
├── wake_word.py             # 唤醒词检测
├── speech_recognition.py    # 语音识别 (ASR)
└── tts.py                   # 文字转语音 (TTS)

src/api/routes/
└── jarvis.py                # REST API 端点
```

---

## 🔌 API 端点

### 1. 语音交互

**POST** `/api/v1/jarvis/interact`

上传音频文件，返回语音回复

**Request**:
- Content-Type: `multipart/form-data`
- Body: `audio` file (WAV/MP3)

**Response**:
- Content-Type: `audio/mpeg`
- Body: MP3 音频数据

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/jarvis/interact \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@my_voice.wav"
```

### 2. 获取状态

**GET** `/api/v1/jarvis/state`

返回当前状态机状态

**Response**:
```json
{
  "state": "idle",
  "duration": 123.45,
  "previous_state": "responding"
}
```

### 3. 重置状态

**POST** `/api/v1/jarvis/reset`

重置状态机到 IDLE

### 4. 获取配置

**GET** `/api/v1/jarvis/config`

返回当前配置

**Response**:
```json
{
  "wake_words": ["嘿鎏灏", "hey liuhao", "jarvis"],
  "asr_language": null,
  "tts_voice": "alloy"
}
```

---

## 🎯 状态机

### 状态定义

1. **IDLE** (待机)
   - 等待唤醒词
   - 可转换到: LISTENING, ERROR

2. **LISTENING** (监听)
   - 录音并识别用户输入
   - 可转换到: PROCESSING, IDLE, ERROR

3. **PROCESSING** (处理)
   - AI 处理请求
   - 可转换到: RESPONDING, IDLE, ERROR

4. **RESPONDING** (响应)
   - TTS 播放回复
   - 可转换到: IDLE, ERROR

5. **ERROR** (错误)
   - 错误状态
   - 可转换到: IDLE

---

## 🗣️ 唤醒词

### 默认唤醒词

- 中文: "嘿鎏灏", "小灏"
- 英文: "hey liuhao", "hi liuhao", "jarvis"
- 其他: "贾维斯"

### 使用方式

1. **单独唤醒**:
   - 用户: "嘿鎏灏"
   - 系统: "我在，请说"

2. **唤醒 + 命令**:
   - 用户: "嘿鎏灏，现在几点了？"
   - 系统: "现在是 14点30分"

---

## 🔧 配置

### 环境变量

需要在 `.env` 中配置:

```bash
# OpenAI API Key (用于 Whisper 和 TTS)
OPENAI_API_KEY=your_api_key_here

# 可选配置
JARVIS_ASR_LANGUAGE=zh  # zh/yue/en
JARVIS_TTS_VOICE=alloy  # alloy/echo/fable/onyx/nova/shimmer
JARVIS_TTS_SPEED=1.0    # 0.25-4.0
```

### 自定义唤醒词

```python
from src.jarvis import JarvisService, WakeWordConfig

config = WakeWordConfig(
    wake_words=["你好鎏灏", "hello jarvis"],
    sensitivity=0.8,
    timeout=5.0
)

jarvis = JarvisService(wake_word_config=config)
```

---

## 💻 使用示例

### Python SDK

```python
from src.jarvis import JarvisService

# 初始化服务
jarvis = JarvisService()

# 处理音频
with open("user_voice.wav", "rb") as f:
    audio_data = f.read()
    
response_audio = await jarvis.process_audio_input(audio_data)

# 保存回复
with open("jarvis_response.mp3", "wb") as f:
    f.write(response_audio)
```

### API 调用 (JavaScript)

```javascript
const formData = new FormData();
formData.append('audio', audioBlob, 'voice.wav');

const response = await fetch('/api/v1/jarvis/interact', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const audioBlob = await response.blob();
const audioUrl = URL.createObjectURL(audioBlob);
const audio = new Audio(audioUrl);
audio.play();
```

---

## 🧪 测试

### 单元测试

```bash
pytest tests/jarvis/test_wake_word.py
pytest tests/jarvis/test_state_machine.py
pytest tests/jarvis/test_service.py
```

### API 测试

```bash
# 获取状态
curl http://localhost:8000/api/v1/jarvis/state

# 获取配置
curl http://localhost:8000/api/v1/jarvis/config

# 语音交互（需要 token）
curl -X POST http://localhost:8000/api/v1/jarvis/interact \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test_voice.wav" \
  --output response.mp3
```

---

## 🚀 后续扩展

### 计划中的功能

1. **本地 Whisper 模型**
   - 支持完全离线运行
   - 提高响应速度

2. **粤语专项优化**
   - 粤语唤醒词
   - 粤语 TTS
   - 粤语俚语支持

3. **多模态交互**
   - 视觉输入（摄像头）
   - 手势识别
   - 表情识别

4. **个性化配置**
   - 用户自定义唤醒词
   - 声音克隆
   - 个性化回复风格

---

## ⚠️ 注意事项

1. **API Key 配置**
   - 必须配置有效的 OpenAI API Key
   - 或使用本地 Whisper/TTS 模型

2. **音频格式**
   - 支持: WAV, MP3, M4A, FLAC
   - 推荐: 16kHz WAV

3. **性能考虑**
   - API 调用有延迟 (~1-3秒)
   - 本地模型响应更快

4. **并发处理**
   - 当前版本单例服务
   - 多用户需要会话管理

---

## 📞 支持

如遇问题，请查看：
- API 文档: http://localhost:8000/docs
- 日志文件: `logs/jarvis.log`
- 状态端点: `/api/v1/jarvis/state`
