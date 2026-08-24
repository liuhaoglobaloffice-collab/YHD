# Header 按键关联修复说明

## 问题描述
原 `frontend/src/components/Header.tsx` 组件中，以下操作按钮没有绑定 `onClick` 事件处理器：
- **搜索按钮**（Search）
- **通知按钮**（Bell/Notifications）
- **设置按钮**（Settings）
- **用户菜单项**（个人信息、系统设置、退出登录）使用 `<a href>` 而非 React Router 导航

这导致用户点击这些按钮时没有任何响应。

---

## 已修复内容

### 1. 添加必要的导入
```typescript
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useUIStore } from "../stores/uiStore";
```

### 2. 实现事件处理器

#### 搜索功能
```typescript
const handleSearch = () => {
  setShowSearchModal(true);
  // TODO: 实现全局搜索弹窗
  showNotification('info', '全局搜索功能开发中');
};
```

#### 通知功能
```typescript
const handleNotifications = () => {
  setShowNotificationsPanel(!showNotificationsPanel);
  // TODO: 实现通知面板
  showNotification('info', '通知中心开发中');
};
```

#### 设置导航
```typescript
const handleSettings = () => {
  navigate('/settings/system');
};
```

#### 退出登录
```typescript
const handleLogout = () => {
  logout();
  showNotification('success', '已退出登录');
  navigate('/login');
};
```

### 3. 修复用户下拉菜单
将 `<a href>` 改为 `<button onClick>` + React Router 导航：
- **个人信息**: `navigate('/settings/profile')`
- **系统设置**: `handleSettings()`
- **退出登录**: `handleLogout()`

### 4. 添加无障碍属性
为所有按钮添加 `aria-label` 属性，提升可访问性。

---

## 后续开发建议

### 短期任务（1-2 周）

#### 1. 全局搜索功能
创建 `frontend/src/components/SearchModal.tsx`：
```typescript
// 实现全局搜索弹窗
// - 支持快捷键（Ctrl/Cmd + K）
// - 搜索范围：订单、客户、供应商、产品
// - 实时搜索建议
// - 快速导航到结果
```

参考文件：
- 后端 API: `src/api/routes/search.py`（需创建）
- 数据索引: 考虑使用 Elasticsearch 或 PostgreSQL Full-Text Search

#### 2. 通知中心
创建 `frontend/src/components/NotificationsPanel.tsx`：
```typescript
// 实现通知面板
// - 显示未读通知数量（红点）
// - 分类：系统通知、订单更新、审批提醒
// - 标记已读/全部已读
// - 通知历史记录
```

后端支持：
- 现有表：`src/knowledge/models/notification.py`（需检查是否可用）
- WebSocket 实时推送（考虑使用 Socket.IO）

#### 3. 键盘快捷键
在 `App.tsx` 或专门的 `KeyboardShortcuts.tsx` 中实现：
```typescript
// 全局快捷键
// Ctrl/Cmd + K: 搜索
// Ctrl/Cmd + N: 通知中心
// Ctrl/Cmd + ,: 设置
// ESC: 关闭弹窗（已部分实现）
```

### 中期任务（1-2 月）

#### 4. 用户个人信息页面
完善 `/settings/profile` 路由：
- 头像上传
- 个人信息编辑（姓名、邮箱、手机）
- 密码修改
- 双因素认证（2FA）

#### 5. 系统设置页面
完善 `/settings/system` 路由：
- 主题切换（已有 `uiStore.theme`）
- 语言设置（中文/英文）
- 通知偏好
- API 密钥管理（针对 CEO 角色）

---

## 技术注意事项

### 状态管理
项目使用 **Zustand** + **localStorage 持久化**：
- `authStore`: 用户认证、登录/登出
- `uiStore`: 主题、侧边栏、通知、加载状态

### 路由导航
使用 **React Router v6**：
- 优先使用 `useNavigate()` hook，避免 `<a href>`
- 保持 URL 与实际页面组件同步

### 无障碍性（Accessibility）
- 所有交互元素必须有 `aria-label`
- 支持键盘导航（Tab、Enter、ESC）
- 焦点管理（弹窗打开时焦点移入）

### 性能优化
- 搜索使用防抖（debounce 300ms）
- 通知列表虚拟滚动（react-window）
- 懒加载设置页面组件

---

## 测试建议

### 单元测试（Jest + React Testing Library）
```typescript
// tests/components/Header.test.tsx
describe('Header Component', () => {
  it('should navigate to settings on settings button click', () => {
    // ...
  });
  
  it('should call logout and navigate to login on logout click', () => {
    // ...
  });
  
  it('should show notification when search button is clicked', () => {
    // ...
  });
});
```

### E2E 测试（Playwright/Cypress）
```typescript
// e2e/header-navigation.spec.ts
test('should logout successfully', async ({ page }) => {
  await page.goto('/dashboard');
  await page.click('[aria-label="用户菜单"]');
  await page.click('text=退出登录');
  await expect(page).toHaveURL('/login');
});
```

---

## 相关文件
- **修复文件**: `frontend/src/components/Header.tsx`
- **状态管理**: 
  - `frontend/src/stores/authStore.ts`
  - `frontend/src/stores/uiStore.ts`
- **后续需创建**:
  - `frontend/src/components/SearchModal.tsx`
  - `frontend/src/components/NotificationsPanel.tsx`
  - `frontend/src/pages/settings/ProfilePage.tsx`
  - `frontend/src/pages/settings/SystemPage.tsx`

---

## 时间估算
- ✅ **Header 按键修复**: 已完成（15 分钟）
- 🔨 **全局搜索功能**: 2-3 天
- 🔨 **通知中心**: 3-4 天
- 🔨 **键盘快捷键**: 1 天
- 🔨 **个人设置页面**: 2-3 天
- 🔨 **系统设置页面**: 2-3 天

**总计**: ~2 周完整开发周期
