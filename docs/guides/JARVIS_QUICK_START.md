# 🎤 贾维斯语音交互系统 - 快速开始指南

**完成时间**: 2026-08-23  
**状态**: ✅ **已完成并可用**

---

## 🚀 立即使用

### 1. 配置 API Key

在 `.env.production` 或 `.env` 中添加：

```bash
# OpenAI API Key (必需)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 2. 重启服务器（如果需要）

```bash
# 停止当前服务器
Get-Process python | Stop-Process

# 重新启动
python start_production.py
```

### 3. 打开贾维斯界面

**方法 A**: 直接在浏览器打开
```
file:///D:/LiuHao-AI-OS/frontend/jarvis-voice.html
```

**方法 B**: 通过 HTTP 服务器
```bash
# 在 frontend 目录
python -m http.server 3000

# 然后访问
http://localhost:3000/jarvis-voice.html
```

---

## 🎯 使用方式

### 基本流程

1. **登录系统**
   - 用户名: `sysadmin`
   - 密码: `SysAdmin123`

2. **开始语音交互**
   - 点击中央的 🎤 按钮开始录音
   - 说出你的指令（可以说 "嘿鎏灏" 唤醒）
   - 再次点击停止录音
   - 等待 Jarvis 处理并播放回复

3. **观察状态**
   - 🟢 就绪 - 等待输入
   - 🎤 监听中 - 正在录音
   - 🧠 处理中 - AI 处理
   - 🗣️ 回复中 - 播放回复

---

## 💬 示例对话

### 唤醒 + 命令
```
用户: "嘿鎏灏，现在几点了？"
贾维斯: "现在是 14点30分"
```

### 先唤醒，后命令
```
用户: "嘿鎏灏"
贾维斯: "我在，请说"
用户: "帮我查一下天气"
贾维斯: "收到指令：帮我查一下天气。功能开发中。"
```

### 直接命令（无唤醒词）
```
用户: "你好"
贾维斯: "你好，我是鎏灏，有什么可以帮你的？"
```

---

## 🎨 界面特性

### 视觉反馈

- **蓝色圆形按钮** - 就绪状态
- **红色脉动按钮** - 正在录音
- **波形动画** - 录音中的视觉效果
- **沙漏图标** - 处理中

### 状态指示

- **顶部状态徽章** - 显示当前系统状态
- **提示文字** - 指导下一步操作
- **识别内容显示** - 展示识别的语音文本
- **回复显示** - 展示 Jarvis 的文字回复

---

## 🔧 API 测试

### 使用 curl 测试

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"sysadmin","password":"SysAdmin123"}' \
  | jq -r '.access_token')

# 2. 测试语音交互
curl -X POST http://localhost:8000/api/v1/jarvis/interact \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@test_voice.wav" \
  --output jarvis_response.mp3

# 3. 播放回复
start jarvis_response.mp3

# 4. 查看状态
curl http://localhost:8000/api/v1/jarvis/state \
  -H "Authorization: Bearer $TOKEN"
```

### 使用 Python 测试

```python
import requests

# 登录
login_resp = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'username': 'sysadmin',
    'password': 'SysAdmin123'
})
token = login_resp.json()['access_token']

# 发送语音
with open('test_voice.wav', 'rb') as f:
    files = {'audio': ('voice.wav', f, 'audio/wav')}
    headers = {'Authorization': f'Bearer {token}'}
    
    resp = requests.post(
        'http://localhost:8000/api/v1/jarvis/interact',
        files=files,
        headers=headers
    )
    
    # 保存回复
    with open('jarvis_response.mp3', 'wb') as out:
        out.write(resp.content)

print("回复已保存到 jarvis_response.mp3")
```

---

## 🐛 故障排除

### 问题 1: 无法访问麦克风

**症状**: 点击按钮后提示 "无法访问麦克风"

**解决**:
- 浏览器需要 HTTPS 或 localhost 才能访问麦克风
- 检查浏览器权限设置，允许麦克风访问
- Chrome: 设置 → 隐私和安全 → 网站设置 → 麦克风

### 问题 2: API 返回 401 Unauthorized

**症状**: 录音后提示认证失败

**解决**:
- Token 可能已过期，重新登录
- 检查后端服务是否正常运行
- 查看浏览器控制台的错误信息

### 问题 3: 无语音回复

**症状**: 处理后没有声音播放

**解决**:
- 检查 OPENAI_API_KEY 是否配置正确
- 查看后端日志: `logs/liuhao_ai_os.log`
- 检查浏览器音量设置
- 尝试手动播放保存的 MP3 文件

### 问题 4: 识别不准确

**症状**: 语音识别错误或识别不到唤醒词

**解决**:
- 说话清晰，减少背景噪音
- 增加唤醒词灵敏度（需修改代码）
- 录音时间太短，多说几秒
- 检查麦克风质量

---

## 📊 性能指标

### 响应时间

- **录音**: 即时开始
- **ASR 识别**: ~1-2 秒
- **处理命令**: ~0.5-1 秒
- **TTS 合成**: ~1-2 秒
- **总时长**: ~3-5 秒

### 音频格式

- **输入**: WAV/MP3/M4A/FLAC
- **输出**: MP3 (128kbps)
- **采样率**: 自动适配
- **推荐**: 16kHz WAV

---

## 🔗 相关链接

- **完整文档**: [docs/features/JARVIS_VOICE_INTERACTION.md](../features/JARVIS_VOICE_INTERACTION.md)
- **API 文档**: http://localhost:8000/docs
- **控制台**: http://localhost:3000/simple-dashboard.html
- **Jarvis 界面**: http://localhost:3000/jarvis-voice.html

---

## 🎉 下一步

贾维斯系统现已完成！你可以：

1. ✅ **使用语音控制** - 通过 Jarvis 界面
2. ✅ **查看 API 文档** - Swagger UI
3. ✅ **集成到应用** - 使用 REST API
4. ⏭️ **继续开发** - 实现路径 D/B/C

---

## 💡 提示

- 首次使用需要授权麦克风访问
- 支持中文、英文、粤语（需配置）
- 可自定义唤醒词和语音风格
- 支持连续对话（开发中）

Happy Talking! 🎤✨
