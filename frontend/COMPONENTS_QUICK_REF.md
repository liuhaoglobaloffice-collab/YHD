# 🎨 UI组件快速参考

## 导入方式
```tsx
import { Button, Card, Input, Badge, Alert, Loading } from '@/components/ui';
```

---

## 1️⃣ Button 按钮
```tsx
<Button variant="primary|secondary|outline|ghost|danger|neon" 
        size="sm|md|lg" 
        isLoading={boolean}>
  按钮文字
</Button>
```

---

## 2️⃣ Card 卡片
```tsx
<Card variant="default|glass|neon" 
      title="标题" 
      subtitle="副标题"
      actions={<Button>操作</Button>}>
  卡片内容
</Card>
```

---

## 3️⃣ Input 输入框
```tsx
import { User } from 'lucide-react';

<Input label="用户名" 
       prefixIcon={User} 
       error="错误消息"
       value={value}
       onChange={(e) => setValue(e.target.value)} />
```

---

## 4️⃣ Badge 徽章
```tsx
<Badge variant="success|warning|error|info|default|purple" 
       size="sm|md|lg">
  状态文字
</Badge>
```

---

## 5️⃣ Alert 提示框
```tsx
<Alert type="success|error|warning|info" 
       title="标题" 
       closable>
  提示内容
</Alert>
```

---

## 6️⃣ Loading 加载
```tsx
<Loading type="spinner|pulse|dots" 
         size="sm|md|lg" 
         text="加载中..." />
```

---

## 7️⃣ Select 下拉选择
```tsx
<Select label="选择项" 
        value={value}
        onChange={setValue}
        options={[
          { value: '1', label: '选项1' },
          { value: '2', label: '选项2' }
        ]} />
```

---

## 8️⃣ Tabs 标签页
```tsx
import { Home, Users } from 'lucide-react';

<Tabs tabs={[
        { id: 'home', label: '首页', icon: Home },
        { id: 'users', label: '用户', icon: Users }
      ]}
      activeTab={activeTab}
      onChange={setActiveTab} />
```

---

## 9️⃣ Dropdown 下拉菜单
```tsx
import { Settings, LogOut } from 'lucide-react';

<Dropdown trigger={<Button>菜单</Button>}
          items={[
            { label: '设置', icon: Settings, onClick: fn },
            { label: '退出', icon: LogOut, onClick: fn, danger: true }
          ]} />
```

---

## 🔟 Modal 模态框
```tsx
<Modal isOpen={isOpen} 
       onClose={() => setIsOpen(false)}
       title="标题">
  <p>模态框内容</p>
  <Button onClick={() => setIsOpen(false)}>关闭</Button>
</Modal>
```

---

## 🎨 通用样式类

### 玻璃态
```tsx
className="glass"        // 标准玻璃态
className="glass-md"     // 中度玻璃态
className="glass-heavy"  // 深度玻璃态
```

### 霓虹文字
```tsx
className="neon-text-blue"    // 蓝色霓虹
className="neon-text-cyan"    // 青色霓虹
className="neon-text-purple"  // 紫色霓虹
```

### 边框发光
```tsx
className="border-glow-blue"  // 蓝色边框发光
className="border-glow-cyan"  // 青色边框发光
```

### 动画
```tsx
className="animate-glow"      // 发光脉冲
className="animate-pulse"     // 脉冲动画
className="animate-float"     // 上下浮动
className="scan-lines"        // 扫描线背景
```

---

## 📐 常用组合示例

### AI员工卡片
```tsx
<Card variant="neon">
  <div className="flex items-center gap-4">
    <div className="w-16 h-16 rounded-full bg-neon-blue/20 border-2 border-neon-blue flex items-center justify-center">
      <User className="w-8 h-8 text-neon-blue" />
    </div>
    <div>
      <h3 className="text-lg font-semibold text-neon-blue">销售经理</h3>
      <Badge variant="success" size="sm">活跃</Badge>
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
    <Users className="w-6 h-6 text-neon-cyan" />
  </div>
</Card>
```

### 表单
```tsx
<Card variant="default" title="新增客户">
  <form className="space-y-4">
    <Input label="公司名称" prefixIcon={Building} />
    <Input label="联系人" prefixIcon={User} />
    <Select label="客户类型" options={options} />
    <div className="flex justify-end gap-2">
      <Button variant="outline">取消</Button>
      <Button variant="primary">保存</Button>
    </div>
  </form>
</Card>
```

---

## 🎯 颜色系统

### 霓虹色
```tsx
text-neon-blue      // #00d9ff 霓虹蓝
text-neon-cyan      // #00ffff 霓虹青
text-neon-purple    // #9900ff 霓虹紫
text-neon-green     // #00ff88 霓虹绿
text-neon-yellow    // #ffd700 霓虹黄
text-neon-red       // #ff0055 霓虹红
```

### 背景色
```tsx
bg-primary-bg       // #0a0e27 主背景
bg-secondary-bg     // #0f1535 次背景
bg-surface-bg       // #1a1f3a 表面
```

### 文字色
```tsx
text-text-primary   // #e0e7ff 主文字
text-text-secondary // #94a3b8 次文字
text-text-muted     // #64748b 弱文字
```

---

**最后更新**: 2026-08-24  
**组件数量**: 10个核心组件  
**完整文档**: 查看 `COMPONENTS_GUIDE.md`
