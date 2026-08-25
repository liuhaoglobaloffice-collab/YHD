/**
 * 阶段3测试脚本 - CEO Dashboard功能测试
 */

import dashboardService from '../services/dashboard';
import workforceAPI from '../services/workforceAPI';
import dashboardAPI from '../services/dashboardAPI';

async function testCEODashboard() {
  console.log('🧪 开始测试 CEO Dashboard 功能...\n');

  const results = {
    total: 0,
    passed: 0,
    failed: 0,
    errors: [] as string[],
  };

  const test = async (name: string, fn: () => Promise<void>) => {
    results.total++;
    try {
      await fn();
      results.passed++;
      console.log(`✅ ${name}`);
    } catch (error) {
      results.failed++;
      const errorMsg = error instanceof Error ? error.message : String(error);
      results.errors.push(`${name}: ${errorMsg}`);
      console.error(`❌ ${name}: ${errorMsg}`);
    }
  };

  // 测试Dashboard API
  await test('Dashboard Stats API', async () => {
    const stats = await dashboardAPI.getStats();
    if (!stats || !stats.timestamp) throw new Error('Invalid stats response');
  });

  await test('Dashboard Trends API', async () => {
    const trends = await dashboardAPI.getTrends(7);
    if (!trends || !trends.period) throw new Error('Invalid trends response');
  });

  await test('Dashboard System Health API', async () => {
    const health = await dashboardAPI.getSystemHealth();
    if (!health || !health.overall_status) throw new Error('Invalid health response');
  });

  await test('Dashboard Alerts API', async () => {
    const alerts = await dashboardAPI.getAlerts();
    if (!Array.isArray(alerts)) throw new Error('Invalid alerts response');
  });

  // 测试Workforce API
  await test('Workforce List API', async () => {
    const employees = await workforceAPI.listEmployees();
    if (!Array.isArray(employees)) throw new Error('Invalid employees response');
  });

  // 测试Dashboard Service
  await test('Dashboard Service - CEO Brief', async () => {
    const brief = await dashboardService.getCEOBrief();
    if (!Array.isArray(brief)) throw new Error('Invalid CEO brief');
    console.log(`   📊 CEO简报: ${brief.length}条`);
  });

  await test('Dashboard Service - Workforce Status', async () => {
    const status = await dashboardService.getWorkforceStatus();
    if (typeof status.total !== 'number') throw new Error('Invalid workforce status');
    console.log(`   👥 AI员工: 总数${status.total}, 活跃${status.active}, 空闲${status.idle}, 异常${status.error}`);
  });

  await test('Dashboard Service - Enterprise Metrics', async () => {
    const metrics = await dashboardService.getEnterpriseMetrics();
    if (!metrics.customers || !metrics.revenue) throw new Error('Invalid metrics');
    console.log(`   📈 企业指标: 客户${metrics.customers.total}, 营收${metrics.revenue.value}`);
  });

  await test('Dashboard Service - Sales Pipeline', async () => {
    const pipeline = await dashboardService.getSalesPipeline();
    if (!Array.isArray(pipeline.stages)) throw new Error('Invalid pipeline');
    console.log(`   🎯 Pipeline: ${pipeline.stages.length}阶段, 转化率${pipeline.conversionRate.toFixed(1)}%`);
  });

  await test('Dashboard Service - Trends', async () => {
    const trends = await dashboardService.getTrends(7);
    if (!Array.isArray(trends.labels)) throw new Error('Invalid trends');
    console.log(`   📉 趋势数据: ${trends.labels.length}天`);
  });

  await test('Dashboard Service - Complete Data', async () => {
    const data = await dashboardService.getDashboardData();
    if (!data || !data.ceoBrief || !data.workforceStatus) throw new Error('Invalid dashboard data');
    console.log(`   ✨ 完整数据加载成功`);
  });

  // 输出测试结果
  console.log('\n' + '='.repeat(60));
  console.log('🎯 测试结果汇总');
  console.log('='.repeat(60));
  console.log(`总计: ${results.total} 个测试`);
  console.log(`通过: ${results.passed} ✅`);
  console.log(`失败: ${results.failed} ❌`);
  console.log(`通过率: ${((results.passed / results.total) * 100).toFixed(1)}%`);

  if (results.errors.length > 0) {
    console.log('\n❌ 失败详情:');
    results.errors.forEach((error, i) => {
      console.log(`${i + 1}. ${error}`);
    });
  }

  return results;
}

// 浏览器console中运行
if (typeof window !== 'undefined') {
  (window as any).testCEODashboard = testCEODashboard;
  console.log('✅ 测试函数已加载');
  console.log('💡 在控制台运行: await testCEODashboard()');
}

export default testCEODashboard;
