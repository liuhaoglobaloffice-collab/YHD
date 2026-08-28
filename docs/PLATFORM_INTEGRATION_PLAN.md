# 外部平台集成详细实施计划

> 版本: 1.0  
> 计划日期: 2026-08-27  
> 当前状态: 框架已存在，需补充真实业务能力

---

## 目录

1. [现状评估](#1-现状评估)
2. [总体架构](#2-总体架构)
3. [实施路线图](#3-实施路线图)
4. [Phase 1: 凭据管理 + 配置化](#4-phase-1-凭据管理--配置化)
5. [Phase 2: WhatsApp 真实集成](#5-phase-2-whatsapp-真实集成)
6. [Phase 3: 企业微信真实集成](#6-phase-3-企业微信真实集成)
7. [Phase 4: Facebook + LinkedIn 集成](#7-phase-4-facebook--linkedin-集成)
8. [Phase 5: 统一收件箱](#8-phase-5-统一收件箱)
9. [Phase 6: 自动化工作流](#9-phase-6-自动化工作流)
10. [Phase 7: 数据同步 + CRM 联动](#10-phase-7-数据同步--crm-联动)
11. [Phase 8: 前端页面](#11-phase-8-前端页面)
12. [Phase 9: 测试 + 部署](#12-phase-9-测试--部署)
13. [API 凭证获取指南](#13-api-凭证获取指南)
14. [风险与依赖](#14-风险与依赖)
15. [工作量估算](#15-工作量估算)

---

## 1. 现状评估

### 1.1 已实现内容

| 模块 | 文件 | 完成度 | 说明 |
|------|------|--------|------|
| 数据模型 | `src/integrations/models.py` | 100% | PlatformAccount/PlatformMessage/PlatformContact 三表完整 |
| 抽象基类 | `src/integrations/base.py` | 100% | PlatformProvider 抽象类 + PlatformRegistry 注册中心 |
| Provider 实现 | `src/integrations/providers.py` | 90% | 4 个真实 Provider + 1 个 MockProvider |
| 平台服务 | `src/integrations/service.py` | 85% | 账号管理/消息收发/联系人/翻译 完整 |
| API 路由 | `src/api/routes/platforms.py` | 90% | 13 个 REST 端点，含权限控制 |
| 翻译服务 | `src/integrations/translation.py` | 80% | 多语言翻译接口完整 |

### 1.2 缺失内容

| 模块 | 优先级 | 现状 | 影响 |
|------|--------|------|------|
| Webhook 接收 | P0 | ❌ 缺失 | 无法接收平台消息 |
| 凭据管理 UI | P0 | ❌ 缺失 | 无法配置真实 API 凭据 |
| 前端平台管理页 | P0 | ❌ 缺失 | 用户无法操作平台 |
| 统一收件箱 | P1 | ❌ 缺失 | 消息分散无法管理 |
| OAuth 流程 | P1 | ❌ 缺失 | 部分平台需 OAuth 授权 |
| 消息模板 | P1 | ❌ 缺失 | WhatsApp 模板消息 |
| CRM 联动 | P1 | ❌ 缺失 | 平台消息→线索 自动化 |
| 自动化工作流 | P2 | ❌ 缺失 | 定时/触发式消息发送 |
| 消息分析 | P2 | ❌ 缺失 | 发送量/回复率等统计 |
| 速率限制 | P2 | ❌ 缺失 | 平台 API 调用配额管理 |

### 1.3 代码质量评估

```
现有代码质量: 🟢 良好

src/integrations/providers.py — 4 个真实 Provider 已实现 API 调用逻辑
  - WhatsAppProvider:   Graph API v19.0, 发送/测试连接 已实现
  - FacebookProvider:   Graph API v19.0, 发送/测试连接 已实现
  - LinkedInProvider:   REST API v2, 发送/测试连接 已实现
  - WeChatWorkProvider: 企业微信 API, 发送/测试连接/Token 管理 已实现

src/integrations/service.py — 服务层编排完整
  - 账号 CRUD ✅
  - 消息发送 + 自动翻译 ✅
  - Mock 模式自动回复 ✅
  - 联系人同步 ✅
  - 权限控制接口已预留 ✅

src/api/routes/platforms.py — 13 个 API 端点
  - 账号管理: 创建/列表/更新/删除/切换/测试连接 (6)
  - 消息: 发送/列表/接收/搜索 (4)
  - 联系人: 列表/同步 (2)
  - 工具: 翻译 (1)
```

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 平台管理页面   │  │ 统一收件箱    │  │ 消息分析仪表盘    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │                 │                    │
┌─────────▼─────────────────▼────────────────────▼────────────┐
│                     API 层 (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ /platforms/* │  │ /webhooks/*  │  │ /crm/leads/*     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │                 │                    │
┌─────────▼─────────────────▼────────────────────▼────────────┐
│                    服务层 (Service)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ PlatformSvc  │  │ WebhookSvc   │  │  CRM Service     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │                 │                    │
┌─────────▼─────────────────▼────────────────────▼────────────┐
│                   Provider 层 (集成)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ WhatsApp │ │ Facebook │ │ LinkedIn │ │ 企业微信      │  │
│  │ Provider │ │ Provider │ │ Provider │ │ Provider      │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬────────┘  │
│       │            │            │              │           │
│  ┌────▼────────────▼────────────▼──────────────▼────────┐  │
│  │              MockProvider (开发回退)                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │                 │                    │
┌─────────▼─────────────────▼────────────────────▼────────────┐
│                   外部平台 API                               │
│  WhatsApp │ Facebook │ LinkedIn │ 企业微信 │ ...            │
│  Cloud API│ Graph API│ REST API │ 企业微信API               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 实施路线图

```
Phase 1: 凭据管理 + 配置化     ████████████░░░░░░  1-2 天
Phase 2: WhatsApp 真实集成     ████████████████░░  2-3 天
Phase 3: 企业微信真实集成        ████████████████░░  2-3 天
Phase 4: Facebook + LinkedIn   ██████████░░░░░░░░  1-2 天
Phase 5: 统一收件箱             ████████████████░░  2-3 天
Phase 6: 自动化工作流           ██████████████████  2-3 天
Phase 7: 数据同步 + CRM 联动    ██████████████░░░░  1-2 天
Phase 8: 前端页面               ██████████████████  2-3 天
Phase 9: 测试 + 部署            ██████████░░░░░░░░  1-2 天
                                   总计: 14-22 天
```

---

## 4. Phase 1: 凭据管理 + 配置化

### 4.1 目标

将 API 凭据从硬编码/环境变量迁移到数据库加密存储，提供凭据管理 API。

### 4.2 新增文件

| 文件 | 用途 |
|------|------|
| `src/core/encryption.py` | 凭据加密/解密工具（AES-256-GCM） |
| `src/api/routes/credentials.py` | 凭据管理 API |

### 4.3 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/integrations/service.py` | `_get_provider()` 增加凭据解密逻辑 |
| `.env` | 增加 `ENCRYPTION_KEY` 环境变量 |
| `src/database/models.py` | 增加 `Credential` 表（可选，复用 `PlatformAccount.credentials` JSON 字段） |

### 4.4 实现细节

```python
# src/core/encryption.py
from cryptography.fernet import Fernet
import os

def get_encryption_key() -> bytes:
    """从环境变量获取加密密钥"""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY 未配置")
    return key.encode()

def encrypt_credentials(credentials: dict) -> dict:
    """加密敏感凭据字段"""
    cipher = Fernet(get_encryption_key())
    encrypted = {}
    for k, v in credentials.items():
        if k in ("access_token", "token", "secret", "app_secret"):
            encrypted[k] = cipher.encrypt(v.encode()).decode()
        else:
            encrypted[k] = v
    return encrypted

def decrypt_credentials(credentials: dict) -> dict:
    """解密凭据"""
    cipher = Fernet(get_encryption_key())
    decrypted = {}
    for k, v in credentials.items():
        if k in ("access_token", "token", "secret", "app_secret"):
            decrypted[k] = cipher.decrypt(v.encode()).decode()
        else:
            decrypted[k] = v
    return decrypted
```

### 4.5 验收标准

- [ ] 凭据加密存储到数据库
- [ ] 读取时自动解密
- [ ] 未配置 ENCRYPTION_KEY 时自动回退 Mock 模式
- [ ] 凭据管理 API 可用（CRUD）

---

## 5. Phase 2: WhatsApp 真实集成

### 5.1 目标

让 WhatsApp Business API 真实可用：发送消息、接收消息（Webhook）、模板消息。

### 5.2 新增文件

| 文件 | 用途 |
|------|------|
| `src/api/routes/webhooks.py` | Webhook 接收端点 |
| `src/integrations/webhook.py` | Webhook 服务（消息解析 + 入库） |
| `src/integrations/templates.py` | 消息模板管理 |

### 5.3 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/integrations/providers.py` | `WhatsAppProvider.fetch_messages()` 改为通过 Webhook 读取 |
| `src/integrations/service.py` | 增加 `process_webhook()` 方法 |
| `src/api/routes/__init__.py` | 注册 webhooks 路由 |

### 5.4 实现细节

#### 5.4.1 Webhook 接收端点

```python
# src/api/routes/webhooks.py
@router.post("/whatsapp/{account_id}")
async def whatsapp_webhook(
    account_id: int,
    body: dict,
    session: AsyncSession = Depends(get_db),
):
    """接收 WhatsApp Cloud API 的 Webhook 回调"""
    service = PlatformService(session)
    await service.process_webhook(account_id, body)
    return {"status": "ok"}

@router.get("/whatsapp/{account_id}")
async def whatsapp_webhook_verify(
    account_id: int,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp Webhook 验证（Meta 要求）"""
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="验证失败")
```

#### 5.4.2 消息模板

```python
# src/integrations/templates.py
WHATSAPP_TEMPLATES = {
    "welcome": {
        "name": "welcome_message",
        "language": "zh_CN",
        "components": [
            {"type": "HEADER", "parameters": [{"type": "text", "text": "{{1}}"}]},
            {"type": "BODY", "parameters": [{"type": "text", "text": "{{1}}"}]},
        ],
    },
    "order_update": {
        "name": "order_update",
        "language": "zh_CN",
        "components": [...],
    },
}
```

### 5.5 配置要求

```bash
# .env
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
```

### 5.6 验收标准

- [ ] 发送真实 WhatsApp 消息到联系人
- [ ] Webhook 接收消息并入库
- [ ] 消息模板管理（创建/列表/发送）
- [ ] 测试连接返回真实状态
- [ ] Mock 模式自动回退

---

## 6. Phase 3: 企业微信真实集成

### 6.1 目标

企业微信消息收发真实可用。

### 6.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/integrations/providers.py` | `WeChatWorkProvider.fetch_messages()` 实现主动拉取 + 增加回调接收 |
| `src/api/routes/webhooks.py` | 增加企业微信 Webhook 回调端点 |

### 6.3 实现细节

企业微信支持两种消息接收方式：
1. **主动拉取** — 调用 `cgi-bin/message/list` 接口（需企业微信服务商）
2. **回调模式** — 配置 HTTP 回调 URL，企业微信推送消息

建议先实现 **主动拉取**，Webhook 回调作为后续优化。

### 6.4 配置要求

```bash
# .env
WECHAT_CORP_ID=your_corp_id
WECHAT_AGENT_SECRET=your_agent_secret
WECHAT_AGENT_ID=your_agent_id
WECHAT_CALLBACK_TOKEN=your_callback_token
WECHAT_CALLBACK_AES_KEY=your_aes_key
```

### 6.5 验收标准

- [ ] 发送真实企业微信消息
- [ ] 主动拉取收件消息
- [ ] 测试连接返回真实状态
- [ ] Mock 模式自动回退

---

## 7. Phase 4: Facebook + LinkedIn 集成

### 7.1 目标

Facebook Messenger 和 LinkedIn 消息收发真实可用。

### 7.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/integrations/providers.py` | 完善 `FacebookProvider` 和 `LinkedInProvider` |
| `src/api/routes/webhooks.py` | 增加 Facebook Webhook 端点 |

### 7.3 实现细节

#### Facebook Messenger
- 需创建 Facebook Page 并获取 Page Access Token
- 通过 Graph API `me/messages` 发送消息
- 通过 Webhook 接收消息（`messages` 字段）
- 需配置 Webhook 订阅（page_messaging 字段）

#### LinkedIn
- 需通过 LinkedIn Developer Portal 创建应用
- 获取 OAuth 2.0 access token（权限: `w_messaging`）
- 调用 `v2/messages` 发送消息
- LinkedIn 消息接收仅支持 Webhook（需申请）

### 7.4 权限要求

| 平台 | 所需权限 |
|------|----------|
| Facebook | `pages_messaging`, `pages_manage_metadata` |
| LinkedIn | `w_messaging`, `r_liteprofile` |

### 7.5 验收标准

- [ ] Facebook Messenger 发送消息
- [ ] Facebook Webhook 接收消息
- [ ] LinkedIn 发送消息
- [ ] 测试连接返回真实状态

---

## 8. Phase 5: 统一收件箱

### 8.1 目标

将四个平台的消息聚合到统一收件箱，支持跨平台回复。

### 8.2 新增文件

| 文件 | 用途 |
|------|------|
| `frontend/src/pages/InboxPage.tsx` | 统一收件箱页面 |
| `frontend/src/services/inbox.ts` | 收件箱 API 服务 |
| `src/api/routes/inbox.py` | 统一收件箱 API |

### 8.3 实现细节

#### 后端 API

```python
# src/api/routes/inbox.py
@router.get("/inbox")
async def get_inbox(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """统一收件箱：跨平台消息聚合"""
    service = PlatformService(session)
    return await service.get_unified_inbox(
        user_ids=visible_user_ids(current_user),
        platform=platform,
        status=status,
        keyword=q,
        page=page,
        page_size=page_size,
    )
```

#### 前端页面

```
统一收件箱布局:
┌─────────────────────────────────────────────────────┐
│ 🔍 搜索  [平台筛选: 全部|WhatsApp|微信|...]         │
├─────────────────┬───────────────────────────────────┤
│  联系人列表      │  消息详情                         │
│                 │                                   │
│  ● WhatsApp     │  ┌─────────────────────────────┐  │
│   张三 (3条未读) │  │ 对方: 收到报价了吗？         │  │
│  ● 企业微信      │  │ 我: 已发送，请查收           │  │
│   李四 (1条未读) │  │ 对方: 好的，谢谢             │  │
│  ○ Facebook     │  └─────────────────────────────┘  │
│   Mark (已读)   │                                   │
│                 │  ┌─────────────────────────────┐  │
│                 │  │ 输入框... [发送] [翻译]     │  │
│                 │  └─────────────────────────────┘  │
├─────────────────┴───────────────────────────────────┤
│  📊 今日消息: 12  待回复: 5  回复率: 58%            │
└─────────────────────────────────────────────────────┘
```

### 8.4 验收标准

- [ ] 跨平台消息聚合展示
- [ ] 平台筛选
- [ ] 关键词搜索
- [ ] 未读标记
- [ ] 统一回复接口
- [ ] 消息统计

---

## 9. Phase 6: 自动化工作流

### 9.1 目标

将平台消息发送集成到 Workflow 引擎，实现自动化触发。

### 9.2 新增文件

| 文件 | 用途 |
|------|------|
| `src/integrations/automation.py` | 自动化规则引擎 |
| `src/workflow/actions/send_message.py` | Workflow 动作：发送消息 |

### 9.3 实现细节

#### 自动化规则

```python
# src/integrations/automation.py
class AutomationRule(BaseModel):
    name: str
    trigger: TriggerType  # NEW_LEAD, NEW_MESSAGE, SCHEDULED
    platform: Optional[str]
    action: ActionType  # SEND_MESSAGE, CREATE_LEAD, UPDATE_CRM
    template: Optional[str]
    filters: dict

class AutomationService:
    async def evaluate(self, event: dict) -> List[AutomationRule]:
        """评估事件匹配的规则"""

    async def execute(self, rule: AutomationRule, context: dict):
        """执行规则"""
```

#### 预置规则示例

| 规则名称 | 触发条件 | 动作 |
|----------|----------|------|
| 新客户自动欢迎 | CRM 创建新线索 | 通过 WhatsApp 发送欢迎消息 |
| 询价自动回复 | 收到供应商消息 | 自动回复"已收到询价，正在处理" |
| 每日跟进提醒 | 定时任务（每天 9:00） | 发送跟进消息给待跟进客户 |
| 异常告警 | 平台连接断开 | 发送企业微信消息给管理员 |

### 9.4 验收标准

- [ ] 自动化规则 CRUD
- [ ] 预置规则 4 条
- [ ] 规则触发执行
- [ ] 执行日志
- [ ] 手动/自动暂停

---

## 10. Phase 7: 数据同步 + CRM 联动

### 10.1 目标

平台联系人与 CRM 线索双向同步，消息自动创建线索活动。

### 10.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/integrations/service.py` | 增加 `sync_to_crm()` 方法 |
| `src/crm/service.py` | 增加 `import_from_platform()` 方法 |

### 10.3 实现细节

#### 平台联系人 → CRM 线索

```python
async def sync_contacts_to_crm(self, account_id: int, owner_user_id: int):
    """将平台联系人同步为 CRM 线索"""
    contacts = await self.list_contacts(account_id, owner_user_id)
    for c in contacts:
        # 检查是否已存在
        existing = await lead_service.find_by_phone(c.phone)
        if not existing:
            await lead_service.create_lead(
                name=c.name,
                phone=c.phone,
                source=f"platform:{c.platform.value}",
                owner_user_id=owner_user_id,
            )
```

#### 消息 → 线索活动

```python
async def message_to_activity(self, message: PlatformMessage):
    """平台消息自动创建为 CRM 线索活动"""
    lead = await lead_service.find_by_phone(message.from_id)
    if lead:
        await lead_service.add_activity(
            lead_id=lead.id,
            type="message",
            description=f"[{message.platform.value}] {message.content[:100]}",
        )
```

### 10.4 验收标准

- [ ] 平台联系人可一键导入 CRM 线索
- [ ] 收到的消息自动关联到对应线索
- [ ] 去重（同一联系人不会重复导入）
- [ ] 同步日志

---

## 11. Phase 8: 前端页面

### 11.1 目标

完整的平台管理前端页面。

### 11.2 新增/修改文件

| 文件 | 用途 |
|------|------|
| `frontend/src/pages/PlatformManagementPage.tsx` | 平台管理总页面 |
| `frontend/src/pages/InboxPage.tsx` | 统一收件箱 |
| `frontend/src/pages/MessageTemplatesPage.tsx` | 消息模板管理 |
| `frontend/src/pages/AutomationRulesPage.tsx` | 自动化规则管理 |
| `frontend/src/services/platforms.ts` | 平台 API 服务 |
| `frontend/src/services/inbox.ts` | 收件箱 API 服务 |
| `frontend/src/services/templates.ts` | 模板 API 服务 |

### 11.3 页面路由

```
/platforms          → 平台管理总页面（列表 + 创建 + 配置）
/platforms/inbox    → 统一收件箱
/platforms/templates → 消息模板管理
/platforms/automation → 自动化规则
```

### 11.4 页面设计

#### 平台管理总页面

```
┌─────────────────────────────────────────────────────────┐
│  AI 外部连接中心                                         │
│  连接状态: 4 平台 / 2 已配置                              │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ WhatsApp │  │ 企业微信  │  │ Facebook │  │LinkedIn│ │
│  │ 🟢 已连接 │  │ 🟡 未配置 │  │ 🔴 未连接 │  │ ⚪ 未配置│ │
│  │ 3 联系人  │  │ 0 联系人  │  │ 0 联系人  │  │ 0 联系人│ │
│  │ 12 消息   │  │ 0 消息    │  │ 0 消息    │  │ 0 消息  │ │
│  │ [配置]    │  │ [配置]    │  │ [配置]    │  │ [配置]  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
├─────────────────────────────────────────────────────────┤
│  📊 平台消息统计                                         │
│  今日发送: 8  今日接收: 12  待回复: 3  回复率: 60%       │
│  ┌─────────────────────────────────────────────────┐     │
│  │ ████████████████░░░░░░░░░░░░░░░ 60%             │     │
│  └─────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────┤
│  📋 最近消息                                              │
│  WhatsApp · 张三 · "收到报价了吗？" · 2 分钟前           │
│  企业微信 · 李四 · "订单已确认" · 15 分钟前               │
│  Facebook · Mark · "Can you ship to USA?" · 1 小时前    │
├─────────────────────────────────────────────────────────┤
│  [⚡ 创建平台账号]  [📥 统一收件箱]  [🤖 自动化规则]     │
└─────────────────────────────────────────────────────────┘
```

### 11.5 验收标准

- [ ] 平台列表展示（4 平台）
- [ ] 创建/配置平台账号
- [ ] 测试连接
- [ ] 启用/停用
- [ ] 删除账号
- [ ] 统一收件箱
- [ ] 消息模板管理
- [ ] 自动化规则管理

---

## 12. Phase 9: 测试 + 部署

### 12.1 测试计划

#### 单元测试

| 测试文件 | 测试内容 | 预计数量 |
|----------|----------|----------|
| `tests/integration/test_platforms.py` | 平台账号 CRUD | 10 |
| `tests/integration/test_messages.py` | 消息发送/接收 | 8 |
| `tests/integration/test_webhooks.py` | Webhook 处理 | 6 |
| `tests/integration/test_automation.py` | 自动化规则 | 8 |
| `tests/test_encryption.py` | 凭据加密 | 4 |

#### 集成测试

| 测试场景 | 说明 |
|----------|------|
| 创建平台账号 → 测试连接 → 发送消息 → 接收消息 | 完整消息链路 |
| 创建自动化规则 → 触发条件 → 执行动作 | 规则引擎验证 |
| 平台联系人 → 同步 CRM → 创建线索 | 数据同步链路 |

#### Mock 测试

所有外部 API 调用使用 `httpx.MockTransport` 或 `responses` 库模拟。

### 12.2 部署配置

```yaml
# docker-compose.yml 新增
services:
  webhook:
    build: .
    ports:
      - "8001:8000"  # Webhook 接收端口（与主 API 分离）
    env_file:
      - .env.production
    depends_on:
      - db
```

### 12.3 验收标准

- [ ] 单元测试 36+ 通过
- [ ] 集成测试 3+ 通过
- [ ] 回归测试 153+ 通过
- [ ] 前端测试 94+ 通过
- [ ] Docker 部署正常

---

## 13. API 凭证获取指南

### 13.1 WhatsApp Business API

```
1. 前往 https://business.facebook.com/ 创建 Business 账号
2. 前往 https://developers.facebook.com/ 创建应用
3. 添加 WhatsApp 产品
4. 设置 Webhook（配置回调 URL + 验证令牌）
5. 生成 Access Token（权限: whatsapp_business_messaging）
6. 获取 Phone Number ID（测试号或申请正式号）
```

### 13.2 企业微信

```
1. 登录 https://work.weixin.qq.com/ 管理后台
2. 创建应用（应用管理 → 自建 → 创建应用）
3. 获取 Corp ID（我的企业 → 企业信息）
4. 获取 Agent ID 和 Secret（应用详情页）
5. 配置回调 URL（应用详情 → 接收消息 → 设置 API 接收）
```

### 13.3 Facebook Messenger

```
1. 创建 Facebook Page
2. 在 Facebook Developers 创建应用
3. 添加 Messenger 产品
4. 生成 Page Access Token
5. 配置 Webhook（订阅 messages 字段）
6. 提交应用审核（如需要公开发布）
```

### 13.4 LinkedIn

```
1. 前往 https://developer.linkedin.com/ 创建应用
2. 获取 Client ID 和 Client Secret
3. 设置 OAuth 2.0 重定向 URL
4. 请求权限: w_messaging, r_liteprofile
5. 获取 Access Token（通过 OAuth 流程）
6. 提交应用审核（如需要公开发布）
```

---

## 14. 风险与依赖

### 14.1 风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 平台 API 变更 | 中 | 抽象 Provider 层，变更只需修改 Provider 实现 |
| API 配额限制 | 中 | 实现速率限制和配额管理 |
| OAuth Token 过期 | 中 | 实现 Token 刷新机制 |
| Webhook 不可达（内网） | 高 | 使用 ngrok/Cloudflare Tunnel 暴露本地服务 |
| 平台审核周期长 | 中 | 先用 Mock 模式开发，审核通过后切换 |
| 数据隐私合规 | 中 | 凭据加密存储，消息内容权限控制 |

### 14.2 外部依赖

| 依赖 | 用途 | 版本要求 |
|------|------|----------|
| `httpx` | 异步 HTTP 请求 | >= 0.27 |
| `cryptography` | 凭据加密 | >= 41.0 |
| `ngrok` | 本地 Webhook 调试（可选） | 最新版 |

### 14.3 前置条件

- [ ] 至少一个平台的真实 API 凭证
- [ ] 公网可访问的 Webhook 接收地址（或 ngrok）
- [ ] 数据库迁移（新增表已存在，无需迁移）

---

## 15. 工作量估算

### 15.1 总工时

| Phase | 描述 | 前端 | 后端 | 测试 | 合计 |
|-------|------|------|------|------|------|
| 1 | 凭据管理 + 配置化 | 0.5 | 1 | 0.5 | **2 天** |
| 2 | WhatsApp 真实集成 | 0 | 2 | 0.5 | **2.5 天** |
| 3 | 企业微信真实集成 | 0 | 1.5 | 0.5 | **2 天** |
| 4 | Facebook + LinkedIn | 0 | 1.5 | 0.5 | **2 天** |
| 5 | 统一收件箱 | 2 | 1 | 0.5 | **3.5 天** |
| 6 | 自动化工作流 | 0.5 | 1.5 | 0.5 | **2.5 天** |
| 7 | 数据同步 + CRM 联动 | 0 | 1 | 0.5 | **1.5 天** |
| 8 | 前端页面 | 2 | 0 | 0.5 | **2.5 天** |
| 9 | 测试 + 部署 | 0 | 0.5 | 1 | **1.5 天** |
| **总计** | | **5 天** | **10 天** | **5 天** | **20 天** |

### 15.2 并行策略

```
Phase 1 + Phase 2 + Phase 3 = 并行（不同开发者）
  ↓
Phase 4 + Phase 8 = 并行（后端 + 前端）
  ↓
Phase 5 + Phase 6 + Phase 7 = 并行（不同开发者）
  ↓
Phase 9 = 收尾
```

### 15.3 建议执行顺序

| 顺序 | Phase | 原因 |
|------|-------|------|
| 1 | Phase 1 | 基础，必须先做 |
| 2 | Phase 2 | 最高优先级平台（WhatsApp 是外贸最常用） |
| 3 | Phase 3 | 第二优先级（中国企业微信高频） |
| 4 | Phase 5 | 统一收件箱提升用户体验最大 |
| 5 | Phase 8 | 前端页面（与 Phase 5 并行） |
| 6 | Phase 7 | CRM 联动（业务价值高） |
| 7 | Phase 6 | 自动化（锦上添花） |
| 8 | Phase 4 | 最低优先级（Facebook/LinkedIn 使用频率较低） |
| 9 | Phase 9 | 收尾 |

---

## 附录

### A. 现有 API 端点清单

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | `/api/v1/platforms/accounts` | 平台账号列表 | ✅ 已存在 |
| POST | `/api/v1/platforms/accounts` | 创建平台账号 | ✅ 已存在 |
| DELETE | `/api/v1/platforms/accounts/{id}` | 删除平台账号 | ✅ 已存在 |
| PATCH | `/api/v1/platforms/accounts/{id}` | 更新平台账号 | ✅ 已存在 |
| POST | `/api/v1/platforms/accounts/{id}/toggle` | 启用/停用 | ✅ 已存在 |
| POST | `/api/v1/platforms/accounts/{id}/test` | 测试连接 | ✅ 已存在 |
| POST | `/api/v1/platforms/accounts/{id}/messages` | 发送消息 | ✅ 已存在 |
| GET | `/api/v1/platforms/accounts/{id}/messages` | 消息列表 | ✅ 已存在 |
| POST | `/api/v1/platforms/accounts/{id}/receive` | 接收消息 | ✅ 已存在 |
| GET | `/api/v1/platforms/accounts/{id}/messages/search` | 搜索消息 | ✅ 已存在 |
| GET | `/api/v1/platforms/accounts/{id}/contacts` | 联系人列表 | ✅ 已存在 |
| POST | `/api/v1/platforms/accounts/{id}/contacts/sync` | 同步联系人 | ✅ 已存在 |
| GET | `/api/v1/platforms/languages` | 支持的语言 | ✅ 已存在 |
| POST | `/api/v1/platforms/translate` | 翻译 | ✅ 已存在 |

### B. 新增 API 端点清单

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| POST | `/api/v1/webhooks/whatsapp/{account_id}` | WhatsApp Webhook 接收 | 2 |
| GET | `/api/v1/webhooks/whatsapp/{account_id}` | WhatsApp Webhook 验证 | 2 |
| POST | `/api/v1/webhooks/wechat/{account_id}` | 企业微信回调 | 3 |
| POST | `/api/v1/webhooks/facebook/{account_id}` | Facebook Webhook 接收 | 4 |
| GET | `/api/v1/webhooks/facebook/{account_id}` | Facebook Webhook 验证 | 4 |
| GET | `/api/v1/platforms/inbox` | 统一收件箱 | 5 |
| GET | `/api/v1/platforms/inbox/stats` | 收件箱统计 | 5 |
| POST | `/api/v1/platforms/inbox/{message_id}/reply` | 回复消息 | 5 |
| POST | `/api/v1/platforms/templates` | 创建消息模板 | 2 |
| GET | `/api/v1/platforms/templates` | 消息模板列表 | 2 |
| POST | `/api/v1/platforms/templates/{id}/send` | 发送模板消息 | 2 |
| POST | `/api/v1/platforms/automation/rules` | 创建自动化规则 | 6 |
| GET | `/api/v1/platforms/automation/rules` | 规则列表 | 6 |
| PUT | `/api/v1/platforms/automation/rules/{id}` | 更新规则 | 6 |
| DELETE | `/api/v1/platforms/automation/rules/{id}` | 删除规则 | 6 |
| POST | `/api/v1/platforms/automation/rules/{id}/toggle` | 启用/停用规则 | 6 |
| GET | `/api/v1/platforms/automation/logs` | 执行日志 | 6 |
| POST | `/api/v1/platforms/sync-crm` | 平台联系人→CRM 同步 | 7 |

### C. 现有代码快速参考

```
src/integrations/
├── __init__.py
├── base.py              # PlatformProvider (ABC) + PlatformRegistry
├── models.py            # PlatformAccount / PlatformMessage / PlatformContact
├── providers.py         # WhatsAppProvider / FacebookProvider / LinkedInProvider / WeChatWorkProvider / MockPlatformProvider
├── service.py           # PlatformService (账号管理 + 消息收发 + 联系人 + 翻译)
└── translation.py       # TranslationService

src/api/routes/
├── platforms.py         # 13 个 REST API 端点
└── webhooks.py          # ❌ 待创建
```

*报告完*