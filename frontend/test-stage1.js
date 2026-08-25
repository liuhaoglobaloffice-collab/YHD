// 鎏灏 AI-OS 阶段1验收测试
// 检查浏览器Console错误

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  // 收集Console消息
  const consoleMessages = [];
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    consoleMessages.push({ type, text });
    console.log(`[${type.toUpperCase()}] ${text}`);
  });
  
  // 收集页面错误
  const pageErrors = [];
  page.on('pageerror', error => {
    pageErrors.push(error.message);
    console.error('[PAGE ERROR]', error.message);
  });
  
  try {
    console.log('🚀 正在访问 http://localhost:3000/ ...');
    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle', timeout: 30000 });
    
    // 等待页面加载完成
    await page.waitForTimeout(3000);
    
    console.log('\n📊 验收结果：');
    console.log('='.repeat(50));
    
    // 统计Console消息
    const errors = consoleMessages.filter(m => m.type === 'error');
    const warnings = consoleMessages.filter(m => m.type === 'warning');
    
    console.log(`✅ 页面加载成功`);
    console.log(`📝 Console消息统计：`);
    console.log(`   - 错误 (error): ${errors.length}`);
    console.log(`   - 警告 (warning): ${warnings.length}`);
    console.log(`   - 页面错误 (pageerror): ${pageErrors.length}`);
    
    // 检查严重错误
    const seriousErrors = errors.filter(e => 
      !e.text.includes('DevTools') && 
      !e.text.includes('manifest') &&
      !e.text.includes('favicon')
    );
    
    if (seriousErrors.length > 0) {
      console.log(`\n❌ 发现 ${seriousErrors.length} 个严重Console错误：`);
      seriousErrors.forEach((e, i) => {
        console.log(`   ${i + 1}. ${e.text}`);
      });
    } else {
      console.log(`\n✅ 无严重Console错误`);
    }
    
    if (pageErrors.length > 0) {
      console.log(`\n❌ 发现 ${pageErrors.length} 个页面错误：`);
      pageErrors.forEach((e, i) => {
        console.log(`   ${i + 1}. ${e}`);
      });
    }
    
    console.log('='.repeat(50));
    
    // 截图保存
    await page.screenshot({ path: 'test-login-page.png', fullPage: true });
    console.log('📸 登录页截图已保存: test-login-page.png');
    
    // 返回状态码
    if (seriousErrors.length === 0 && pageErrors.length === 0) {
      console.log('\n🎉 阶段1 - 浏览器Console测试通过！');
      process.exit(0);
    } else {
      console.log('\n⚠️ 阶段1 - 存在需要关注的错误');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
