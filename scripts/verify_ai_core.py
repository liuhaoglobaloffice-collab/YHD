import json
import time
import urllib.request

BASE = 'http://localhost/api/v1'
TS = str(int(time.time()))
USER = f'ui_core_{TS}'
PASS = 'Core#2026Aa!'

# 1. API 注册 OWNER 账号
req = urllib.request.Request(
    f'{BASE}/auth/register',
    data=json.dumps({'username': USER, 'email': f'{USER}@liuhao-os.dev', 'password': PASS}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('register:', r.status)
except urllib.error.HTTPError as e:
    print('register HTTP', e.code, '->', e.read().decode()[:300])
    raise SystemExit(1)
except Exception as e:
    print('register error:', str(e)[:200])
    raise SystemExit(1)

# 2. API 登录拿 token，直接注入 localStorage 再访问页面（等价真实登录态）
req = urllib.request.Request(
    f'{BASE}/auth/login',
    data=json.dumps({'username': USER, 'password': PASS}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
token = None
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        body = json.loads(r.read())
        token = body.get('access_token') or body.get('token')
        print('login OK, token len:', len(token) if token else None)
except Exception as e:
    print('login failed:', str(e)[:200])
    raise SystemExit(1)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})

    # 注入 token（与前端 services/auth 的存储 key 一致）
    page.goto('http://localhost/login', wait_until='domcontentloaded')
    page.evaluate(f'''() => {{
        localStorage.setItem('liuhao_auth_token', '{token}');
        localStorage.setItem('liuhao_user', JSON.stringify({{ username: '{USER}', role: 'OWNER' }}));
    }}''')
    page.goto('http://localhost/', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path='d:/LiuHao-AI-OS/scripts/shot_dash.png')

    audit = page.evaluate('''() => {
        const out = { url: location.pathname,
                      aiCoreChip: null, sidebarChip: null, ceoLive: null,
                      healthDot: !!document.querySelector('.health-dot'),
                      hologramPulse: !!document.querySelector('.hologram-pulse'),
                      ceoLiveDot: !!document.querySelector('.ceo-live-dot'),
                      headerStatus: !!document.querySelector('.header-status'),
                      statusDotCount: document.querySelectorAll('.ai-status-dot').length };
        const chip = document.querySelector('.ai-core-chip');
        if (chip) {
            const cs = getComputedStyle(chip.querySelector('.ai-status-dot'));
            out.aiCoreChip = { text: chip.textContent.trim(), title: chip.title, dotBg: cs.backgroundColor };
        }
        const sb = document.querySelector('.hologram-chip');
        if (sb) out.sidebarChip = { text: sb.textContent.trim(), color: getComputedStyle(sb).color };
        const cl = document.querySelector('.ceo-live');
        if (cl) out.ceoLive = cl.textContent.trim();
        return out;
    }''')
    print('=== desktop 1440px AI Core audit ===')
    print(json.dumps(audit, ensure_ascii=False, indent=2))

    # 平板 900px
    page.set_viewport_size({'width': 900, 'height': 700})
    page.wait_for_timeout(500)
    page.screenshot(path='d:/LiuHao-AI-OS/scripts/shot_900.png')

    # 手机 375px
    page.set_viewport_size({'width': 375, 'height': 812})
    page.wait_for_timeout(500)
    page.screenshot(path='d:/LiuHao-AI-OS/scripts/shot_mobile.png')
    mobile = page.evaluate('''() => {
        const label = document.querySelector('.ai-core-label');
        const header = document.querySelector('.app-header');
        return { labelHidden: label ? getComputedStyle(label).display === 'none' : null,
                 headerOverflow: header ? header.scrollWidth > window.innerWidth : null };
    }''')
    print('=== mobile 375px ===')
    print(json.dumps(mobile, ensure_ascii=False))

    browser.close()
    print('DONE')
