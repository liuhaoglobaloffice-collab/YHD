# 🎨 鎏灏 AI-OS UI组件库使用手册

## 快速开始

```tsx
import { Button, Card, Input, Badge, Alert, Loading } from '@/components/ui';
```

---

## 组件目录

1. [Button](#1-button-按钮)
2. [Card](#2-card-卡片)
3. [Input](#3-input-输入框)
4. [Badge](#4-badge-徽章)
5. [Alert](#5-alert-提示框)
6. [Loading](#6-loading-加载动画)
7. [Select](#7-select-下拉选择)
8. [Tabs](#8-tabs-标签页)
9. [Dropdown](#9-dropdown-下拉菜单)
10. [Modal](#10-modal-模态框)

---

## 1. Button 按钮

### 变体（Variants）
| 变体 | 描述 | 适用场景 |
|------|------|----------|
| `primary` | 霓虹蓝主按钮 | 主要操作（提交、确认） |
| `secondary` | 青色次要按钮 | 次要操作 |
| `outline` | 透明轮廓按钮 | 取消、返回 |
| `ghost` | 玻璃态幽灵按钮 | 工具栏按钮 |
| `danger` | 红色危险按钮 | 删除、禁用 |
| `neon` | 极致发光按钮 | 语音激活、特殊功能 |

### 尺寸（Sizes）
- `sm` - 小按钮（px-3 py-1.5）
- `md` - 中按钮（px-4 py-2）- 默认
- `lg` - 大按钮（px-6 py-3）

### 示例代码
```tsx
// 基础用法
<Button variant="primary" size="md" onClick={handleClick}>
  提交
</Button>

// 加载状态
<Button variant="primary" isLoading={true}>
  保存中...
</Button>

// 禁用状态
<Button variant="danger" disabled>
  已禁用
</Button>

// 带图标
<Button variant="neon" size="lg">
  <Mic className="mr-2" />
  嘿鎏灏
</Button>
```

### 视觉效果
- ✅ 霓虹发光（box-shadow）
- ✅ 悬停放大（hover:scale-105）
- ✅ 点击涟漪动画
- ✅ 加载时旋转图标

---

## 2. Card 卡片

### 变体（Variants）
| 变体 | 描述 | 适用场景 |
|------|------|----------|
| `default` | 标准玻璃态卡片 | 通用内容容器 |
| `glass` | 深度玻璃态（更模糊） | 重要信息、统计数据 |
| `neon` | 霓虹发光卡片+扫描线 | 高亮功能、AI员工卡片 |

### 示例代码
```tsx
// 基础卡片
<Card variant="default">
  <p>卡片内容</p>
</Card>

// 带标题和操作按钮
<Card 
  variant="glass" 
  title="AI员工监控"
  subtitle="实时状态"
  actions={
    <Button variant="ghost" size="sm">
      <Settings className="w-4 h-4" />
    </Button>
  }
>
  <p>6个AI员工正在运行</p>
</Card>

// 霓虹发光卡片
<Card variant="neon" title="系统健康度">
  <div className="text-center">
    <div className="text-5xl font-bold text-neon-cyan">98%</div>
  </div>
</Card>
```

### 视觉效果
- ✅ 玻璃态背景（backdrop-blur）
- ✅ 悬停放大（hover:scale-102）
- ✅ 边框发光（neon变体）
- ✅ 扫描线动画（neon变体）

---

## 3. Input 输入框

### Props
| 属性 | 类型 | 描述 |
|------|------|------|
| `label` | string | 标签文字 |
| `prefixIcon` | React.ComponentType | 前缀图标（Lucide组件） |
| `suffixIcon` | React.ComponentType | 后缀图标 |
| `error` | string | 错误消息 |
| `helperText` | string | 辅助文字 |

### 示例代码
```tsx
import { User, Mail, Lock } from 'lucide-react';

// 带前缀图标
<Input 
  label="用户名" 
  prefixIcon={User}
  placeholder="输入用户名"
  value={username}
  onChange={(e) => setUsername(e.target.value)}
/>

// 带错误提示
<Input 
  label="邮箱" 
  prefixIcon={Mail}
  type="email"
  error="邮箱格式不正确"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>

// 密码输入框
<Input 
  label="密码" 
  prefixIcon={Lock}
  type="password"
  helperText="至少8位字符"
/>
```

### 视觉效果
- ✅ 玻璃态背景
- ✅ 霓虹蓝边框（30%透明度）
- ✅ 聚焦时ring发光（2px）
- ✅ 错误状态红色边框+消息

---

## 4. Badge 徽章

### 变体（Variants）
| 变体 | 颜色 | 适用场景 |
|------|------|----------|
| `default` | 灰色 | 默认状态 |
| `success` | 绿色 | 成功、活跃、在线 |
| `warning` | 黄色 | 警告、待处理 |
| `error` | 红色 | 错误、离线、失败 |
| `info` | 蓝色 | 信息提示 |
| `purple` | 紫色 | 特殊标记 |

### 尺寸（Sizes）
- `sm` - 小徽章（text-xs px-2 py-0.5）
- `md` - 中徽章（text-sm px-2.5 py-0.5）- 默认
- `lg` - 大徽章（text-base px-3 py-1）

### 示例代码
```tsx
// AI员工状态
<Badge variant="success" size="sm">活跃</Badge>
<Badge variant="warning" size="sm">待机</Badge>
<Badge variant="error" size="sm">离线</Badge>

// 订单状态
<Badge variant="info">待审核</Badge>
<Badge variant="success">已完成</Badge>
<Badge variant="purple">VIP</Badge>
```

### 视觉效果
- ✅ 霓虹色背景（透明度10%）
- ✅ 霓虹色边框
- ✅ 圆角胶囊形状
- ✅ 文字发光效果

---

## 5. Alert 提示框

### 类型（Types）
| 类型 | 颜色 | 图标 | 适用场景 |
|------|------|------|----------|
| `success` | 绿色 | ✓ | 操作成功 |
| `error` | 红色 | ✕ | 操作失败 |
| `warning` | 黄色 | ⚠ | 警告提示 |
| `info` | 蓝色 | ℹ | 信息提示 |

### 示例代码
```tsx
// 成功提示
<Alert type="success" title="保存成功" closable>
  客户信息已更新
</Alert>

// 错误提示
<Alert type="error" title="操作失败">
  网络连接超时，请稍后重试
</Alert>

// 警告提示
<Alert type="warning" title="数据未保存">
  您有未保存的更改，确认离开吗？
</Alert>

// 信息提示（无关闭按钮）
<Alert type="info" title="系统维护通知">
  系统将于今晚22:00-23:00进行维护
</Alert>
```

### 视觉效果
- ✅ 玻璃态背景+模糊
- ✅ 左侧彩色边框（4px）
- ✅ 图标自动匹配类型
- ✅ 可选关闭按钮（X）

---

## 6. Loading 加载动画

### 类型（Types）
| 类型 | 描述 | 适用场景 |
|------|------|----------|
| `spinner` | 旋转圆环 | 按钮加载、局部加载 |
| `pulse` | 脉冲光点 | 页面加载 |
| `dots` | 跳动点阵 | 文本加载 |

### 尺寸（Sizes）
- `sm` - 小（w-4 h-4）
- `md` - 中（w-8 h-8）- 默认
- `lg` - 大（w-12 h-12）

### 示例代码
```tsx
// 旋转加载
<Loading type="spinner" size="md" text="加载中..." />

// 页面中心加载
<div className="flex items-center justify-center h-screen">
  <Loading type="pulse" size="lg" text="系统初始化中..." />
</div>

// 文本加载
<Loading type="dots" size="sm" text="处理中" />

// 无文字
<Loading type="spinner" size="sm" />
```

### 视觉效果
- ✅ 霓虹青色动画
- ✅ Spinner: 旋转圆环（0.8秒周期）
- ✅ Pulse: 渐变脉冲光（1.5秒周期）
- ✅ Dots: 三点跳动（1.4秒错位）

---

## 7. Select 下拉选择

### Props
| 属性 | 类型 | 描述 |
|------|------|------|
| `options` | `{value: string, label: string}[]` | 选项列表 |
| `value` | string | 当前值 |
| `onChange` | (value: string) => void | 变化回调 |
| `label` | string | 标签文字 |
| `error` | string | 错误消息 |

### 示例代码
```tsx
const [country, setCountry] = useState('cn');

<Select
  label="国家/地区"
  value={country}
  onChange={setCountry}
  options={[
    { value: 'cn', label: '中国' },
    { value: 'us', label: '美国' },
    { value: 'jp', label: '日本' },
  ]}
/>
```

### 视觉效果
- ✅ 玻璃态背景
- ✅ 霓虹蓝边框
- ✅ 下拉箭头动画
- ✅ 选项悬停高亮

---

## 8. Tabs 标签页

### Props
| 属性 | 类型 | 描述 |
|------|------|------|
| `tabs` | `TabItem[]` | 标签列表 |
| `activeTab` | string | 当前激活的tab |
| `onChange` | (id: string) => void | 切换回调 |

### 示例代码
```tsx
const [activeTab, setActiveTab] = useState('overview');

<Tabs
  tabs={[
    { id: 'overview', label: '总览', icon: BarChart },
    { id: 'employees', label: 'AI员工', icon: Users },
    { id: 'tasks', label: '任务', icon: CheckSquare },
  ]}
  activeTab={activeTab}
  onChange={setActiveTab}
/>

{/* 内容区域 */}
{activeTab === 'overview' && <OverviewContent />}
{activeTab === 'employees' && <EmployeesContent />}
```

### 视觉效果
- ✅ 激活状态：霓虹蓝下划线+发光
- ✅ 未激活：半透明文字
- ✅ 悬停：文字变亮
- ✅ 切换动画：下划线滑动

---

## 9. Dropdown 下拉菜单

### Props
| 属性 | 类型 | 描述 |
|------|------|------|
| `items` | `DropdownItem[]` | 菜单项列表 |
| `trigger` | React.ReactNode | 触发元素 |

### 示例代码
```tsx
import { Settings, User, LogOut } from 'lucide-react';

<Dropdown
  trigger={
    <Button variant="ghost" size="sm">
      <User className="w-5 h-5" />
    </Button>
  }
  items={[
    { 
      label: '个人设置', 
      icon: Settings,
      onClick: () => navigate('/settings') 
    },
    { 
      label: '退出登录', 
      icon: LogOut,
      onClick: handleLogout,
      danger: true
    },
  ]}
/>
```

### 视觉效果
- ✅ 玻璃态下拉面板
- ✅ 霓虹蓝边框
- ✅ 菜单项悬停高亮
- ✅ 危险项红色文字

---

## 10. Modal 模态框

### Props
| 属性 | 类型 | 描述 |
|------|------|------|
| `isOpen` | boolean | 是否打开 |
| `onClose` | () => void | 关闭回调 |
| `title` | string | 标题 |
| `children` | React.ReactNode | 内容 |

### 示例代码
```tsx
const [isOpen, setIsOpen] = useState(false);

<Button onClick={() => setIsOpen(true)}>
  打开模态框
</Button>

<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="确认删除"
>
  <p className="text-text-secondary mb-4">
    确定要删除该客户吗？此操作不可恢复。
  </p>
  <div className="flex justify-end gap-2">
    <Button variant="outline" onClick={() => setIsOpen(false)}>
      取消
    </Button>
    <Button variant="danger" onClick={handleDelete}>
      确认删除
    </Button>
  </div>
</Modal>
```

### 视觉效果
- ✅ 背景蒙层（黑色60%透明度+模糊）
- ✅ 玻璃态内容区
- ✅ 霓虹蓝标题栏
- ✅ ESC键关闭

---

## 🎨 通用样式类

### Tailwind工具类
```tsx
// 玻璃态效果
className="glass"        // 标准玻璃态
className="glass-md"     // 中度玻璃态
className="glass-heavy"  // 深度玻璃态

// 霓虹文字
className="neon-text-blue"    // 蓝色霓虹文字
className="neon-text-cyan"    // 青色霓虹文字
className="neon-text-purple"  // 紫色霓虹文字

// 边框发光
className="border-glow-blue"   // 蓝色边框发光
className="border-glow-cyan"   // 青色边框发光

// 卡片效果
className="card-hover"    // 卡片悬停效果（放大+阴影）

// 动画
className="animate-glow"       // 发光脉冲
className="animate-scan"       // 扫描线
className="animate-float"      // 上下浮动
className="animate-shake"      // 震动
className="scan-lines"         // 扫描线背景
```

### 颜色系统
```tsx
// 霓虹色
text-neon-blue      bg-neon-blue      border-neon-blue
text-neon-cyan      bg-neon-cyan      border-neon-cyan
text-neon-purple    bg-neon-purple    border-neon-purple
text-neon-green     bg-neon-green     border-neon-green
text-neon-yellow    bg-neon-yellow    border-neon-yellow
text-neon-red       bg-neon-red       border-neon-red

// 表面颜色
bg-primary-bg       // 主背景 #0a0e27
bg-secondary-bg     // 次背景 #0f1535
bg-surface-bg       // 表面 #1a1f3a

// 文字颜色
text-text-primary   // 主文字 #e0e7ff
text-text-secondary // 次文字 #94a3b8
text-text-muted     // 弱文字 #64748b
```

---

## 📦 组合示例

### AI员工卡片
```tsx
<Card variant="neon" className="relative overflow-hidden">
  <div className="flex items-center gap-4">
    <div className="relative">
      <div className="w-16 h-16 rounded-full bg-neon-blue/20 border-2 border-neon-blue flex items-center justify-center">
        <User className="w-8 h-8 text-neon-blue" />
      </div>
      <div className="absolute -bottom-1 -right-1">
        <Badge variant="success" size="sm">活跃</Badge>
      </div>
    </div>
    <div>
      <h3 className="text-lg font-semibold text-neon-blue">销售经理</h3>
      <p className="text-sm text-text-secondary">处理客户开发与商机分析</p>
    </div>
  </div>
</Card>
```

### 数据统计卡片
```tsx
<Card variant="glass">
  <div className="flex items-center justify-between">
    <div>
      <p className="text-text-secondary text-sm">总客户数</p>
      <p className="text-3xl font-bold text-neon-cyan mt-1">1,234</p>
    </div>
    <div className="w-12 h-12 rounded-full bg-neon-cyan/20 flex items-center justify-center">
      <Users className="w-6 h-6 text-neon-cyan" />
    </div>
  </div>
</Card>
```

### 表单示例
```tsx
<Card variant="default" title="新增客户">
  <form onSubmit={handleSubmit} className="space-y-4">
    <Input
      label="公司名称"
      prefixIcon={Building}
      value={companyName}
      onChange={(e) => setCompanyName(e.target.value)}
      error={errors.companyName}
    />
    
    <Input
      label="联系人"
      prefixIcon={User}
      value={contactName}
      onChange={(e) => setContactName(e.target.value)}
    />
    
    <Select
      label="客户类型"
      value={customerType}
      onChange={setCustomerType}
      options={[
        { value: 'enterprise', label: '企业客户' },
        { value: 'individual', label: '个人客户' },
      ]}
    />
    
    <div className="flex justify-end gap-2 pt-4">
      <Button variant="outline" onClick={onCancel}>
        取消
      </Button>
      <Button variant="primary" type="submit" isLoading={loading}>
        保存
      </Button>
    </div>
  </form>
</Card>
```

---

## 🚀 最佳实践

### 1. 组件选择原则
- **按钮**: 主要操作用`primary`，危险操作用`danger`，工具栏用`ghost`
- **卡片**: 通用内容用`default`，重点内容用`glass`，特殊功能用`neon`
- **徽章**: 状态标识用对应颜色（成功=绿，警告=黄，错误=红）

### 2. 布局建议
- 使用`grid`或`flex`布局组合卡片
- 卡片间距：`gap-4`（1rem）或`gap-6`（1.5rem）
- 内容区padding：`p-6`（1.5rem）

### 3. 响应式
- 所有组件支持响应式
- 移动端建议：卡片`grid-cols-1`，桌面端`grid-cols-2`或`grid-cols-3`

---

**最后更新**: 2026-08-24  
**版本**: 阶段1 - v1.0  
**组件数量**: 10个核心组件
