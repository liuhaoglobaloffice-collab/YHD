const p = require('puppeteer-core');
(async() => {
  let browser;
  const paths = ['/usr/bin/chromium-browser', '/usr/bin/chromium', '/usr/bin/google-chrome-stable'];
  for (const ep of paths) {
    try { browser = await p.launch({executablePath: ep, args: ['--no-sandbox','--disable-setuid-sandbox']}); break; }
    catch(e) {}
  }
  if (!browser) { console.log('no chromium'); process.exit(1); }
  const page = await browser.newPage({viewport: {width: 1440, height: 900}});
  try {
    await page.goto('http://host.docker.internal/', {waitUntil: 'networkidle', timeout: 20000});
  } catch(e) {
    console.log('goto failed', e.message);
    await browser.close(); process.exit(1);
  }
  await page.screenshot({path: '/tmp/dash.png'});
  const hits = await page.evaluate(() => {
    const all = document.querySelectorAll('*');
    const r = [];
    for (const el of all) {
      const cs = getComputedStyle(el);
      const w = parseFloat(cs.width), h = parseFloat(cs.height);
      if (cs.borderRadius && cs.borderRadius.includes('50%') && (w > 100 || h > 100)) {
        r.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className || '').substring(0, 60),
          w: Math.round(w), h: Math.round(h),
          br: cs.borderRadius.substring(0, 20),
          bg: (cs.background || '').substring(0, 60),
          pos: cs.position, disp: cs.display
        });
      }
    }
    return r;
  });
  console.log(JSON.stringify(hits, null, 2));
  await browser.close();
})();
