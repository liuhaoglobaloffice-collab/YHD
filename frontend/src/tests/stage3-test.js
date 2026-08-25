/**
 * 阶段3验收测试 - Node.js版本
 * 测试Dashboard API、Workforce API和Services
 */

const axios = require('axios');

const API_BASE = 'http://localhost:8000/api/v1';
const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTYzNjYxNjk5Iiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzkwMTc5NzgwfQ.LQs1goc00nlsEBt8x8jNT447u87pqbj-qJ9J8QY1Ung';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json',
  },
});

const results = {
  total: 0,
  passed: 0,
  failed: 0,
  errors: [],
};

async function test(name, fn) {
  results.total++;
  process.stdout.write(`Testing: ${name} ... `);
  try {
    await fn();
    results.passed++;
    console.log('✅ PASS');
    return true;
  } catch (error) {
    results.failed++;
    console.log(`❌ FAIL: ${error.message}`);
    results.errors.push({ name, error: error.message });
    return false;
  }
}

async function testDashboardAPIs() {
  console.log('\n📊 测试 Dashboard APIs\n');

  await test('Dashboard Stats', async () => {
    const { data } = await api.get('/dashboard/stats');
    if (!data.timestamp) throw new Error('No timestamp');
    if (!data.suppliers) throw new Error('No suppliers data');
    console.log(`   Stats: ${data.suppliers.total} suppliers, ${data.business_metrics.active_orders} orders`);
  });

  await test('Dashboard Trends', async () => {
    const { data } = await api.get('/dashboard/trends', { params: { days: 7 } });
    if (!data.period) throw new Error('No period data');
    if (!Array.isArray(data.daily_new_suppliers)) throw new Error('Invalid daily_new_suppliers');
    console.log(`   Trends: ${data.daily_new_suppliers.length} days of data`);
  });

  await test('System Health', async () => {
    const { data } = await api.get('/dashboard/system-health');
    if (!data.overall_status) throw new Error('No overall_status');
    if (!Array.isArray(data.components)) throw new Error('Invalid components');
    console.log(`   Health: ${data.overall_status}, ${data.components.length} components`);
  });

  await test('Dashboard Alerts', async () => {
    const { data } = await api.get('/dashboard/alerts');
    if (!Array.isArray(data)) throw new Error('Invalid alerts response');
    console.log(`   Alerts: ${data.length} alerts`);
  });

  await test('Recent Activity', async () => {
    const { data } = await api.get('/dashboard/recent-activity', { params: { limit: 10 } });
    if (!Array.isArray(data)) throw new Error('Invalid activity response');
    console.log(`   Activity: ${data.length} items`);
  });
}

async function testWorkforceAPIs() {
  console.log('\n👥 测试 Workforce APIs\n');

  await test('List Employees', async () => {
    const { data } = await api.get('/workforce/employees');
    if (!Array.isArray(data)) throw new Error('Invalid employees response');
    console.log(`   Employees: ${data.length} AI employees`);
  });
}

async function testFrontendComponents() {
  console.log('\n🎨 测试 Frontend Components\n');

  await test('Charts Components Exist', async () => {
    const fs = require('fs');
    const path = require('path');
    
    const chartsDir = path.join(__dirname, '../components/Charts');
    const files = ['LineChart.tsx', 'BarChart.tsx', 'FunnelChart.tsx', 'RadarChart.tsx', 'index.ts'];
    
    for (const file of files) {
      const filePath = path.join(chartsDir, file);
      if (!fs.existsSync(filePath)) {
        throw new Error(`Missing file: ${file}`);
      }
    }
    console.log(`   Charts: All 4 chart components exist`);
  });

  await test('Dashboard Services Exist', async () => {
    const fs = require('fs');
    const path = require('path');
    
    const servicesDir = path.join(__dirname, '../services');
    const files = ['dashboard.ts', 'websocket.ts'];
    
    for (const file of files) {
      const filePath = path.join(servicesDir, file);
      if (!fs.existsSync(filePath)) {
        throw new Error(`Missing file: ${file}`);
      }
    }
    console.log(`   Services: dashboard.ts and websocket.ts exist`);
  });

  await test('Dashboard Store Exists', async () => {
    const fs = require('fs');
    const path = require('path');
    
    const storePath = path.join(__dirname, '../stores/dashboardStore.ts');
    if (!fs.existsSync(storePath)) {
      throw new Error('dashboardStore.ts not found');
    }
    console.log(`   Store: dashboardStore.ts exists`);
  });

  await test('CEO Dashboard Component Exists', async () => {
    const fs = require('fs');
    const path = require('path');
    
    const dashboardPath = path.join(__dirname, '../pages/overview/CEODashboard.tsx');
    if (!fs.existsSync(dashboardPath)) {
      throw new Error('CEODashboard.tsx not found');
    }
    console.log(`   Component: CEODashboard.tsx exists`);
  });
}

async function runAllTests() {
  console.log('\n' + '='.repeat(70));
  console.log('🚀 LiuHao AI-OS 阶段3验收测试');
  console.log('='.repeat(70));

  try {
    await testDashboardAPIs();
    await testWorkforceAPIs();
    await testFrontendComponents();
  } catch (error) {
    console.error('\n❌ 测试执行错误:', error.message);
  }

  console.log('\n' + '='.repeat(70));
  console.log('📊 测试结果汇总');
  console.log('='.repeat(70));
  console.log(`总计: ${results.total} 个测试`);
  console.log(`通过: ${results.passed} ✅`);
  console.log(`失败: ${results.failed} ❌`);
  console.log(`通过率: ${((results.passed / results.total) * 100).toFixed(1)}%`);

  if (results.errors.length > 0) {
    console.log('\n❌ 失败详情:');
    results.errors.forEach((item, i) => {
      console.log(`${i + 1}. ${item.name}`);
      console.log(`   Error: ${item.error}`);
    });
  }

  console.log('\n' + '='.repeat(70));
  
  if (results.failed === 0) {
    console.log('✅ 所有测试通过！阶段3验收标准达标。');
  } else {
    console.log('❌ 存在失败测试，请修复后重新测试。');
  }

  console.log('='.repeat(70) + '\n');

  process.exit(results.failed > 0 ? 1 : 0);
}

runAllTests();
