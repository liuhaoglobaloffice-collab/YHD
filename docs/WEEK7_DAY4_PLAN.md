# Week 7 Day 4 工作计划

**日期**: 2026-08-23  
**阶段**: Phase 1 Week 7 - 供应商管理前端  
**当前进度**: Day 4 / 7

---

## 📋 Week 7 总体目标

Week 7 的任务是完成供应商管理的前端界面：
- ✅ Day 1-2: 供应商列表页面 (已完成)
- ✅ Day 3: 供应商详情页面 (已完成)
- 🎯 **Day 4: 供应商数据可视化 + 风险评估交互**
- ⏳ Day 5: 数据采集配置界面
- ⏳ Day 6: 供应商创建/编辑表单
- ⏳ Day 7: 集成测试 + Week 7 总结

---

## 🎯 Day 4 核心任务

### 任务 1: 供应商仪表板页面 (2-3 小时)

**目标**: 创建供应商管理的数据可视化仪表板

**要实现的组件**:
1. **SupplierDashboardPage.tsx** (主页面)
   - 供应商总数统计卡片
   - 按状态分布（活跃/待审核/黑名单）
   - 按业务类型分布
   - 按风险等级分布
   - 本月新增趋势图
   - 高风险供应商预警列表

2. **SupplierStatsCards.tsx** (统计卡片组件)
   - 总供应商数
   - 活跃供应商数
   - 高风险供应商数
   - 本月新增数

3. **SupplierRiskDistributionChart.tsx** (风险分布图表)
   - 使用 recharts 绘制饼图/柱状图
   - 显示 极低/低/中/高 风险占比

4. **SupplierTypeDistributionChart.tsx** (业务类型分布)
   - 制造商/贸易商/代理商/服务商 分布

5. **HighRiskSupplierAlert.tsx** (高风险预警组件)
   - 列出所有高风险供应商
   - 显示风险分数和主要风险因素
   - 快速跳转到详情页

**API 集成**:
- `GET /api/v1/ceo/suppliers/stats` - 统计数据
- `GET /api/v1/ceo/suppliers/risk-distribution` - 风险分布
- `GET /api/v1/suppliers/high-risk` - 高风险列表

---

### 任务 2: 风险评估交互增强 (2 小时)

**目标**: 在供应商详情页增强风险评估功能

**要实现的功能**:
1. **触发风险评估按钮**
   - 在详情页顶部添加"重新评估风险"按钮
   - 调用 `POST /api/v1/suppliers/{id}/assess-risk`
   - 显示评估进度（Loading 状态）
   - 评估完成后自动刷新风险历史

2. **风险评估结果展示优化**
   - 显示风险分数趋势图（历史评估）
   - 突出显示当前风险等级
   - 展示详细的风险因素列表
   - 显示 AI 生成的建议（recommendations）

3. **风险因素可视化**
   - 创建 `RiskFactorsCard.tsx` 组件
   - 以卡片形式展示各个风险因素
   - 显示权重和描述
   - 使用图标和颜色编码

4. **风险趋势图表**
   - 创建 `RiskTrendChart.tsx` 组件
   - 使用 recharts 绘制折线图
   - X 轴: 评估日期
   - Y 轴: 风险分数 (0-100)

---

### 任务 3: 响应式优化和样式调整 (1 小时)

**目标**: 确保供应商管理界面在各设备上良好显示

**要优化的内容**:
1. 移动端适配
   - 统计卡片在小屏幕上垂直堆叠
   - 表格支持横向滚动
   - 图表自适应容器宽度

2. 赛博朋克主题强化
   - 使用深色背景 (#0B0E14, #1E293B)
   - 霓虹色强调 (cyan #22D3EE, orange #F97316)
   - 扫描线动画效果
   - 数据加载骨架屏

3. 交互动画
   - 卡片 hover 效果
   - 按钮点击反馈
   - 数据加载过渡动画

---

## 📂 需要创建的文件

```
frontend/src/
├── pages/business/
│   └── SupplierDashboardPage.tsx          (新建)
├── components/supplier/                    (新建目录)
│   ├── SupplierStatsCards.tsx             (新建)
│   ├── SupplierRiskDistributionChart.tsx  (新建)
│   ├── SupplierTypeDistributionChart.tsx  (新建)
│   ├── HighRiskSupplierAlert.tsx          (新建)
│   ├── RiskFactorsCard.tsx                (新建)
│   └── RiskTrendChart.tsx                 (新建)
└── services/
    └── supplierAPI.ts                      (更新: 添加Dashboard API)
```

---

## 🔧 技术栈

- **框架**: React 18 + TypeScript
- **路由**: React Router v6
- **状态管理**: Zustand
- **图表库**: recharts
- **样式**: Tailwind CSS
- **图标**: lucide-react
- **HTTP**: axios

---

## ✅ 验收标准

### 功能完整性
- [ ] 供应商仪表板页面可以访问并显示数据
- [ ] 所有统计卡片正确显示数值
- [ ] 风险分布图表正确渲染
- [ ] 业务类型分布图表正确渲染
- [ ] 高风险预警列表正确显示
- [ ] 可以从仪表板跳转到供应商详情页
- [ ] 详情页可以触发风险评估
- [ ] 风险评估完成后自动更新数据
- [ ] 风险因素卡片正确展示
- [ ] 风险趋势图表正确渲染

### 用户体验
- [ ] 所有 API 调用有 Loading 状态
- [ ] API 错误有友好的提示
- [ ] 空数据状态有合适的占位符
- [ ] 页面响应迅速（< 1秒）
- [ ] 移动端显示正常

### 代码质量
- [ ] TypeScript 类型定义完整
- [ ] 组件解耦合理
- [ ] 无 console 错误
- [ ] 代码格式规范

---

## 📊 预计工作量

| 任务 | 预计时间 | 优先级 |
|------|---------|--------|
| 供应商仪表板页面 | 2-3 小时 | P0 |
| 风险评估交互增强 | 2 小时 | P0 |
| 响应式优化 | 1 小时 | P1 |
| **总计** | **5-6 小时** | - |

---

## 🚀 开始执行

执行顺序：
1. 创建 `components/supplier/` 目录和基础组件
2. 更新 `supplierAPI.ts` 添加 Dashboard API
3. 创建 `SupplierDashboardPage.tsx` 主页面
4. 实现统计卡片和图表组件
5. 在详情页添加风险评估交互
6. 响应式优化和样式调整
7. 测试所有功能

---

**计划制定人**: Kiro  
**计划审批**: CEO  
**开始时间**: 2026-08-23 10:00  
**预计完成**: 2026-08-23 17:00
