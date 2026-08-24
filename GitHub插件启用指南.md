# 🐙 GitHub 插件启用指南

## ✅ 插件状态
- **版本:** 0.1.6
- **位置:** D:\CodexSystem\.codex\plugins\cache\openai-api-curated\github\11c74d6b\
- **状态:** ⚠️ 已缓存,待授权启用

---

## 🔑 必需的授权

GitHub 插件需要以下授权才能工作:

### 1. GitHub OAuth 连接器
- **Connector ID:** `connector_76869538009648d5b282a4bb21c3d157`
- **用途:** 访问你的 GitHub 仓库、PRs 和 Issues

### 2. GitHub Personal Access Token (可选)
- **环境变量:** `GITHUB_PAT_TOKEN`
- **用途:** 增强的 API 访问权限

---

## 📋 启用步骤

### 方法 1: 通过 Codex 应用界面 (推荐)

1. **打开插件管理**
   - 在 Codex 应用中点击左下角 ⚙️ 设置
   - 选择 "Plugins" (插件)

2. **找到 GitHub 插件**
   - 在插件列表中搜索 "GitHub"
   - 你会看到插件图标和描述

3. **安装并授权**
   - 点击 "Install" 或 "Enable" 按钮
   - 会弹出 GitHub OAuth 授权页面
   - 点击 "Authorize OpenAI" 授权访问

4. **完成设置**
   - 授权成功后,插件会自动启用
   - 你会在插件列表中看到 ✅ 已启用标记

---

### 方法 2: 通过 GitHub 网页授权

如果应用内授权失败,可以:

1. 访问 https://github.com/settings/apps
2. 找到 "OpenAI Codex" 或相关授权应用
3. 授权必要的权限:
   - ✅ Read access to code
   - ✅ Read and write access to issues and pull requests
   - ✅ Read access to actions (CI/CD)

---

### 方法 3: 设置 Personal Access Token (高级)

如果需要更强大的功能,可以设置 PAT:

1. **创建 GitHub PAT**
   - 访问 https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限:
     - ✅ `repo` (完整仓库访问)
     - ✅ `workflow` (GitHub Actions)
     - ✅ `read:org` (组织信息)
   - 复制生成的 token

2. **配置环境变量**
   ```powershell
   # 临时设置 (当前会话)
   $env:GITHUB_PAT_TOKEN = "ghp_your_token_here"
   
   # 永久设置 (系统环境变量)
   [System.Environment]::SetEnvironmentVariable('GITHUB_PAT_TOKEN', 'ghp_your_token_here', 'User')
   ```

3. **重启 Codex 应用**
   - 使环境变量生效

---

## 🎯 插件功能

启用后,你可以使用以下功能:

### 📦 仓库管理
```
"列出我的 GitHub 仓库"
"查看 LiuHao-AI-OS 仓库的详细信息"
"这个仓库有多少 stars?"
```

### 🔍 Pull Request 审查
```
"查看我的待审查 PR"
"这个 PR #123 有什么改动?"
"帮我审查最新的 PR"
"PR 中有什么问题吗?"
```

### 🐛 Issues 管理
```
"列出所有未关闭的 issues"
"创建一个新的 issue: [标题]"
"关闭 issue #456"
"这个 issue 的讨论内容是什么?"
```

### 🔧 CI/CD 调试
```
"为什么最近的 CI 失败了?"
"查看 GitHub Actions 运行日志"
"这个构建为什么报错?"
"重新运行失败的 workflow"
```

### 📝 代码审查
```
"检查这个 PR 的代码质量"
"这个改动会引入 bug 吗?"
"建议的改进是什么?"
```

---

## 🔍 验证插件是否启用

### 检查方法 1: 在 Codex 中测试
输入:
```
"列出我的 GitHub 仓库"
```

如果插件正常工作,会显示你的仓库列表。

### 检查方法 2: 查看插件状态
在 Codex 设置 → 插件 中,GitHub 插件应该显示为 "已启用" 或 "Enabled"。

---

## 🛠️ 故障排查

### 问题 1: 授权失败
**症状:** 点击 Install 后没有反应或授权页面无法加载

**解决方案:**
1. 检查网络连接
2. 清除浏览器缓存
3. 重启 Codex 应用
4. 尝试使用系统默认浏览器

---

### 问题 2: 插件无法访问仓库
**症状:** "没有权限访问该仓库" 错误

**解决方案:**
1. 确认已授权 OpenAI 访问你的 GitHub 账号
2. 检查仓库是否为私有(需要额外权限)
3. 重新授权插件
4. 考虑设置 PAT token

---

### 问题 3: API 限流
**症状:** "API rate limit exceeded" 错误

**解决方案:**
1. 等待 API 限制重置(通常 1 小时)
2. 设置 GitHub PAT token(更高的限额)
3. 减少 API 调用频率

---

### 问题 4: MCP 服务器连接失败
**症状:** 插件加载失败或功能不可用

**解决方案:**
1. 检查网络连接到 `https://api.githubcopilot.com`
2. 确认防火墙没有阻止连接
3. 重启 Codex 应用

---

## 📊 插件配置详情

### MCP 服务器
- **类型:** HTTP
- **URL:** https://api.githubcopilot.com/mcp/
- **认证:** Bearer Token (通过环境变量 GITHUB_PAT_TOKEN)

### App 连接器
- **ID:** connector_76869538009648d5b282a4bb21c3d157
- **提供商:** GitHub OAuth

---

## 🎓 使用技巧

### 高效工作流

1. **晨间检查**
   ```
   "列出我的所有待审查 PR"
   "有新的 issues 需要处理吗?"
   "检查最近的 CI 状态"
   ```

2. **代码审查**
   ```
   "打开 PR #123"
   "这个改动的影响范围?"
   "有潜在的安全问题吗?"
   "建议批准这个 PR 吗?"
   ```

3. **问题追踪**
   ```
   "列出标记为 'bug' 的 issues"
   "创建 issue: 修复登录页面的 CSS 问题"
   "关联这个 commit 到 issue #789"
   ```

---

## 🔐 安全建议

1. **保护你的 PAT Token**
   - ⚠️ 不要在代码中硬编码 token
   - ⚠️ 不要提交 token 到版本控制
   - ✅ 使用环境变量存储
   - ✅ 定期轮换 token

2. **最小权限原则**
   - 只授权必需的权限
   - 定期审查授权应用
   - 及时撤销不需要的访问

3. **监控访问**
   - 定期检查 GitHub 安全日志
   - 注意异常的 API 调用

---

## 📚 相关资源

- **GitHub 文档:** https://docs.github.com/
- **GitHub API:** https://docs.github.com/en/rest
- **Codex 插件文档:** 在 Codex 中输入 `@openai-docs github plugin`

---

## ✅ 下一步

1. [ ] 在 Codex 应用中启用 GitHub 插件
2. [ ] 完成 OAuth 授权
3. [ ] 测试基本功能(列出仓库)
4. [ ] (可选) 设置 PAT token 以获得更多功能
5. [ ] 开始使用插件提升开发效率!

---

**需要帮助?**
- 在 Codex 中说: "GitHub 插件有问题"
- 或查看 Codex 设置 → 帮助与支持

---

*最后更新: 2026-08-24*
*插件版本: 0.1.6*
