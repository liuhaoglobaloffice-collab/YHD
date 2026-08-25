# 🎯 Week 21-22: 外贸业务核心插件开发指南

> **最重要的2周！直接创造业务价值！每天节省6小时，效率提升10倍！** ⭐⭐⭐

**总时间**: 14天  
**预计代码量**: ~8,000行  
**ROI**: 24个月150%

---

## 📊 Week 21-22 概览

| Week | 插件名称 | 天数 | 核心价值 |
|------|---------|------|---------|
| **Week 21** | **海外客户开发插件** | 5天 | 自动开发海外客户，效率提升10倍 |
| **Week 22** | **供应商开发+智能报告** | 9天 | 智能找供应商+AI报告，节省2-3小时/次 |

---

## 🌍 Week 21: 海外客户开发插件（5天）

### **Day 1-2: LinkedIn销售助手插件** ⭐⭐⭐⭐⭐

> **核心价值**: 每天自动开发50-100个潜在客户，节省4-5小时手动操作

#### **功能设计**

```python
# plugins/linkedin_sales/plugin.py

from playwright.async_api import async_playwright
from typing import List, Dict
import asyncio

class LinkedInSalesPlugin:
    """
    LinkedIn全流程客户开发
    
    核心功能：
    1. 智能搜索目标客户
    2. 批量发送连接请求
    3. AI生成个性化消息
    4. 多轮自动跟进
    5. 同步到CRM
    """
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.daily_limit = 20  # 防封号：每天最多20个连接请求
        self.sent_today = 0
    
    async def search_prospects(
        self,
        keywords: str,
        location: str = "United States",
        industry: str = None,
        company_size: str = "51-200"
    ) -> List[Dict]:
        """
        搜索目标客户
        
        参数：
        - keywords: 职位关键词 (如 "Buyer", "Procurement Manager", "Importer")
        - location: 地区 (如 "United States", "Germany")
        - industry: 行业 (如 "Medical Devices", "Electronics")
        - company_size: 公司规模 (如 "51-200", "201-500")
        
        返回：
        - 潜在客户列表（姓名/公司/职位/LinkedIn URL）
        """
        
        async with async_playwright() as p:
            # 启动浏览器
            self.browser = await p.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # 登录LinkedIn
            await self._login()
            
            # 构建搜索URL
            search_url = self._build_search_url(
                keywords=keywords,
                location=location,
                industry=industry,
                company_size=company_size
            )
            
            # 访问搜索页面
            await self.page.goto(search_url)
            await self.page.wait_for_load_state('networkidle')
            
            # 提取客户列表
            prospects = []
            
            # 滚动加载更多结果
            for i in range(5):  # 加载5页，约50个结果
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
            
            # 解析客户信息
            cards = await self.page.query_selector_all('.reusable-search__result-container')
            
            for card in cards:
                prospect = await self._extract_prospect_info(card)
                if prospect:
                    prospects.append(prospect)
            
            await self.browser.close()
            
            return prospects
    
    async def send_connection_request(
        self,
        prospect_url: str,
        message_template: str = None
    ) -> bool:
        """
        发送连接请求
        
        参数：
        - prospect_url: LinkedIn个人主页URL
        - message_template: 消息模板（可选）
        
        返回：
        - 是否成功发送
        """
        
        # 检查每日限额
        if self.sent_today >= self.daily_limit:
            print(f"⚠️ 已达到每日限额({self.daily_limit})，防止封号")
            return False
        
        try:
            # 访问个人主页
            await self.page.goto(prospect_url)
            await self.page.wait_for_load_state('networkidle')
            
            # 点击"Connect"按钮
            connect_button = await self.page.query_selector('button:has-text("Connect")')
            if not connect_button:
                print("⚠️ 未找到Connect按钮（可能已发送或无法连接）")
                return False
            
            await connect_button.click()
            await asyncio.sleep(1)
            
            # 如果有消息模板，添加备注
            if message_template:
                # 点击"Add a note"
                add_note_button = await self.page.query_selector('button:has-text("Add a note")')
                if add_note_button:
                    await add_note_button.click()
                    await asyncio.sleep(1)
                    
                    # AI生成个性化消息
                    personalized_message = await self._generate_personalized_message(
                        prospect_url,
                        message_template
                    )
                    
                    # 输入消息
                    message_input = await self.page.query_selector('textarea[name="message"]')
                    await message_input.fill(personalized_message)
            
            # 点击"Send"
            send_button = await self.page.query_selector('button:has-text("Send")')
            await send_button.click()
            
            self.sent_today += 1
            print(f"✅ 已发送连接请求 ({self.sent_today}/{self.daily_limit})")
            
            # 随机延迟（防止被检测为机器人）
            await asyncio.sleep(random.uniform(30, 60))
            
            return True
        
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False
    
    async def _generate_personalized_message(
        self,
        prospect_url: str,
        template: str
    ) -> str:
        """
        AI生成个性化消息
        
        步骤：
        1. 抓取客户资料（姓名/公司/职位/背景）
        2. 用GPT-4生成个性化消息
        """
        
        # 抓取客户资料
        profile = await self._scrape_profile(prospect_url)
        
        # 调用GPT-4
        prompt = f"""
        请基于以下模板和客户信息，生成一条个性化的LinkedIn连接请求消息。
        
        模板：
        {template}
        
        客户信息：
        - 姓名：{profile['name']}
        - 公司：{profile['company']}
        - 职位：{profile['title']}
        - 行业：{profile['industry']}
        
        要求：
        1. 字数控制在200字以内
        2. 语气专业友好
        3. 突出我们的产品优势
        4. 引起对方兴趣
        
        个性化消息：
        """
        
        response = await openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专业的B2B销售专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        message = response.choices[0].message.content.strip()
        
        return message
    
    async def auto_follow_up(
        self,
        prospect_id: str,
        sequence: List[Dict]
    ):
        """
        自动跟进序列
        
        示例序列：
        Day 1: 发送连接请求
        Day 3: 连接后感谢消息 + 公司介绍
        Day 7: 分享成功案例
        Day 14: 询问是否有需求
        Day 30: 发送新产品信息
        """
        
        for step in sequence:
            # 等待指定天数
            await asyncio.sleep(step['delay_days'] * 24 * 3600)
            
            # 发送消息
            await self.send_message(
                prospect_id=prospect_id,
                message=step['message']
            )
    
    async def sync_to_crm(
        self,
        prospect: Dict
    ):
        """
        同步到鎏灏CRM
        
        同步内容：
        - 客户基本信息
        - LinkedIn URL
        - 聊天历史
        - 商机评分
        """
        
        await crm_api.create_customer({
            "name": prospect['name'],
            "company": prospect['company'],
            "title": prospect['title'],
            "linkedin_url": prospect['url'],
            "source": "LinkedIn自动开发",
            "score": await self._calculate_score(prospect)
        })

# 使用示例
async def main():
    plugin = LinkedInSalesPlugin()
    
    # 1. 搜索目标客户
    prospects = await plugin.search_prospects(
        keywords="Buyer OR Procurement Manager OR Importer",
        location="United States",
        industry="Medical Devices",
        company_size="51-200"
    )
    
    print(f"找到 {len(prospects)} 个潜在客户")
    
    # 2. 批量发送连接请求
    for prospect in prospects[:20]:  # 每天20个
        success = await plugin.send_connection_request(
            prospect_url=prospect['url'],
            message_template="""
            Hi {name},
            
            I noticed your role at {company}. We specialize in {product_category} 
            with FDA/CE certifications. Would love to connect and explore potential 
            collaboration opportunities.
            
            Best regards,
            外贸CEO
            """
        )
        
        if success:
            # 3. 同步到CRM
            await plugin.sync_to_crm(prospect)
```

#### **防封号策略**

```python
# 防封号措施

class AntiDetection:
    """防止LinkedIn检测为机器人"""
    
    @staticmethod
    async def random_delay():
        """随机延迟（模拟人类行为）"""
        await asyncio.sleep(random.uniform(2, 5))
    
    @staticmethod
    async def random_mouse_move(page):
        """随机鼠标移动"""
        await page.mouse.move(
            random.randint(0, 1920),
            random.randint(0, 1080)
        )
    
    @staticmethod
    def daily_limits():
        """每日限额"""
        return {
            "connection_requests": 20,  # 连接请求
            "messages": 50,             # 私信
            "profile_views": 100,       # 主页访问
        }
    
    @staticmethod
    async def human_like_scrolling(page):
        """模拟人类滚动"""
        for _ in range(3):
            await page.evaluate('window.scrollBy(0, 300)')
            await asyncio.sleep(random.uniform(0.5, 1.5))
```

---

### **Day 3-4: 邮件营销引擎** ⭐⭐⭐⭐⭐

> **核心价值**: 每天发送200+cold email，打开率25-30%，回复率5-8%

#### **功能设计**

```python
# plugins/email_outreach/plugin.py

class EmailOutreachPlugin:
    """
    邮件营销全流程自动化
    
    核心功能：
    1. 邮箱发现（网站/LinkedIn/API）
    2. 邮箱验证（SMTP验证）
    3. AI生成邮件
    4. 批量发送（SMTP轮转）
    5. 追踪分析（打开率/回复率）
    6. 智能跟进
    """
    
    async def find_emails(
        self,
        company_domain: str
    ) -> List[str]:
        """
        从多渠道发现邮箱
        
        渠道：
        1. 公司官网爬取
        2. LinkedIn推测 (firstname.lastname@domain.com)
        3. Hunter.io API
        4. Apollo.io API
        5. RocketReach API
        """
        
        emails = []
        
        # 1. 爬取官网
        website_emails = await self._scrape_website(f"https://{company_domain}")
        emails.extend(website_emails)
        
        # 2. LinkedIn推测
        employees = await self._get_linkedin_employees(company_domain)
        for employee in employees:
            # 推测邮箱格式
            predicted_emails = self._predict_email_format(
                first_name=employee['first_name'],
                last_name=employee['last_name'],
                domain=company_domain
            )
            emails.extend(predicted_emails)
        
        # 3. Hunter.io API
        hunter_emails = await self._query_hunter_io(company_domain)
        emails.extend(hunter_emails)
        
        # 去重
        emails = list(set(emails))
        
        return emails
    
    async def verify_email(
        self,
        email: str
    ) -> Dict:
        """
        验证邮箱有效性
        
        验证步骤：
        1. 语法检查
        2. DNS/MX记录检查
        3. SMTP验证（连接邮件服务器）
        4. 一次性邮箱检测
        5. 角色邮箱检测（info@/admin@）
        
        返回：
        - valid: 是否有效
        - deliverable: 是否可送达
        - score: 质量评分 (0-100)
        """
        
        result = {
            "email": email,
            "valid": False,
            "deliverable": False,
            "score": 0,
            "reason": ""
        }
        
        # 1. 语法检查
        if not self._validate_syntax(email):
            result['reason'] = "语法错误"
            return result
        
        # 2. DNS检查
        domain = email.split('@')[1]
        if not await self._check_mx_records(domain):
            result['reason'] = "域名无MX记录"
            return result
        
        # 3. SMTP验证
        is_deliverable = await self._smtp_verify(email)
        if not is_deliverable:
            result['reason'] = "邮箱不存在"
            return result
        
        # 4. 一次性邮箱检测
        if self._is_disposable(email):
            result['reason'] = "一次性邮箱"
            return result
        
        # 5. 角色邮箱检测
        if self._is_role_email(email):
            result['score'] = 50  # 角色邮箱质量较低
            result['reason'] = "角色邮箱"
        else:
            result['score'] = 90  # 个人邮箱质量高
        
        result['valid'] = True
        result['deliverable'] = True
        
        return result
    
    async def generate_email(
        self,
        recipient: Dict,
        campaign_type: str = "cold_outreach"
    ) -> Dict:
        """
        AI生成个性化邮件
        
        步骤：
        1. 分析收件人背景（LinkedIn）
        2. 选择邮件模板
        3. GPT-4生成主题行
        4. GPT-4生成正文
        5. A/B测试变体
        """
        
        # 1. 获取收件人背景
        profile = await self._get_recipient_profile(recipient['email'])
        
        # 2. 构建prompt
        prompt = f"""
        请为以下收件人生成一封专业的cold email。
        
        收件人信息：
        - 姓名：{profile['name']}
        - 公司：{profile['company']}
        - 职位：{profile['title']}
        - 行业：{profile['industry']}
        
        我的公司：
        - 名称：鎏灏外贸
        - 产品：{self.company_info['products']}
        - 优势：{self.company_info['advantages']}
        
        邮件要求：
        1. 主题行吸引人（少于50字）
        2. 正文简洁（150-200字）
        3. 突出产品价值
        4. 包含明确的CTA（行动号召）
        5. 专业友好的语气
        
        请生成：
        1. 主题行（3个变体，用于A/B测试）
        2. 邮件正文
        """
        
        response = await openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个B2B邮件营销专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        
        return {
            "subject_lines": self._extract_subjects(content),
            "body": self._extract_body(content),
            "recipient": recipient,
        }
    
    async def send_campaign(
        self,
        emails: List[Dict],
        schedule: Dict = None
    ):
        """
        批量发送邮件
        
        智能发送策略：
        1. SMTP轮转（多账号防封）
        2. 时区优化（收件人当地时间）
        3. 发送速率（每小时50封）
        4. 暖身策略（新邮箱逐步增量）
        """
        
        # SMTP账号池
        smtp_accounts = [
            {"host": "smtp.gmail.com", "user": "account1@gmail.com", "password": "xxx"},
            {"host": "smtp.gmail.com", "user": "account2@gmail.com", "password": "xxx"},
            {"host": "smtp.outlook.com", "user": "account3@outlook.com", "password": "xxx"},
        ]
        
        current_account_index = 0
        sent_count = 0
        
        for email_data in emails:
            # 1. 选择SMTP账号（轮转）
            smtp_account = smtp_accounts[current_account_index]
            current_account_index = (current_account_index + 1) % len(smtp_accounts)
            
            # 2. 计算最佳发送时间（收件人时区）
            send_time = self._calculate_optimal_time(email_data['recipient'])
            
            # 3. 等待到发送时间
            await self._wait_until(send_time)
            
            # 4. 发送邮件
            success = await self._send_email(
                smtp_account=smtp_account,
                to=email_data['recipient']['email'],
                subject=email_data['subject'],
                body=email_data['body'],
                tracking_pixel=True  # 添加追踪像素
            )
            
            if success:
                sent_count += 1
                
                # 5. 记录发送
                await self._log_sent_email(email_data)
            
            # 6. 速率控制（每小时50封）
            await asyncio.sleep(72)  # 72秒 ≈ 50封/小时
    
    async def track_campaign(
        self,
        campaign_id: str
    ) -> Dict:
        """
        追踪邮件营销效果
        
        追踪指标：
        - 发送成功率
        - 打开率（像素追踪）
        - 点击率（链接追踪）
        - 回复率
        - 退订率
        - 垃圾邮件投诉率
        """
        
        metrics = await self.db.query(f"""
            SELECT 
                COUNT(*) as sent,
                SUM(CASE WHEN opened THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN clicked THEN 1 ELSE 0 END) as clicked,
                SUM(CASE WHEN replied THEN 1 ELSE 0 END) as replied
            FROM email_tracking
            WHERE campaign_id = '{campaign_id}'
        """)
        
        return {
            "sent": metrics['sent'],
            "opened": metrics['opened'],
            "open_rate": metrics['opened'] / metrics['sent'] * 100,
            "clicked": metrics['clicked'],
            "click_rate": metrics['clicked'] / metrics['sent'] * 100,
            "replied": metrics['replied'],
            "reply_rate": metrics['replied'] / metrics['sent'] * 100,
        }
    
    async def auto_follow_up(
        self,
        campaign_id: str
    ):
        """
        智能自动跟进
        
        跟进逻辑：
        1. 未打开 → 2天后重发（不同主题）
        2. 已打开未回复 → 3天后跟进
        3. 已回复 → 转交给贾维斯/人工
        4. 退订 → 停止发送
        """
        
        emails = await self.db.get_campaign_emails(campaign_id)
        
        for email in emails:
            if not email['opened']:
                # 未打开 → 重发
                await self.resend_with_new_subject(email)
            
            elif email['opened'] and not email['replied']:
                # 已打开未回复 → 跟进
                await self.send_follow_up(email)
            
            elif email['replied']:
                # 已回复 → 通知
                await self.notify_reply(email)
```

---

### **Day 5: WhatsApp Business插件** ⭐⭐⭐⭐

> **核心价值**: 即时沟通，提升客户体验，转化率提升30%

```python
# plugins/whatsapp_business/plugin.py

class WhatsAppBusinessPlugin:
    """
    WhatsApp客户管理
    
    核心功能：
    1. 批量群发消息
    2. 自动回复
    3. 客户分组管理
    4. 聊天记录同步
    """
    
    async def send_bulk_messages(
        self,
        contacts: List[str],
        template: str,
        variables: Dict = None
    ):
        """
        批量群发消息
        
        注意：
        - 必须使用官方模板（防封）
        - 支持个性化变量
        - 可发送多媒体（图片/文档）
        """
        
        for contact in contacts:
            message = template.format(**variables) if variables else template
            
            await self.send_message(
                to=contact,
                message=message
            )
            
            # 速率控制
            await asyncio.sleep(3)
    
    async def auto_reply(
        self,
        message: Dict
    ) -> str:
        """
        智能自动回复
        
        回复策略：
        1. 关键词匹配（价格/产品/订单）
        2. 贾维斯AI回复（复杂问题）
        3. 转人工（无法处理）
        """
        
        # 1. 检测关键词
        if "price" in message['text'].lower():
            return await self._get_price_info(message)
        
        # 2. 贾维斯AI回复
        return await jarvis.reply(message['text'])
```

---

## 🏭 Week 22: 供应商开发 + 智能报告（9天）

### **Day 1-2: 1688供应商搜索插件** ⭐⭐⭐⭐⭐

```python
# plugins/alibaba_sourcing/plugin.py

class AlibabaSourcePlugin:
    """
    1688/阿里巴巴供应商开发
    
    核心功能：
    1. 多平台搜索供应商
    2. 智能过滤
    3. 批量询价
    4. 询盘自动回复
    5. 数据同步
    """
    
    async def search_suppliers(
        self,
        product_keywords: str,
        filters: Dict = None
    ) -> List[Dict]:
        """
        搜索供应商
        
        平台：
        - 1688.com
        - 阿里巴巴国际站
        - Made-in-China
        - Global Sources
        
        过滤条件：
        - 金牌供应商
        - 交易保障
        - 价格范围
        - 地区（广东/浙江）
        - MOQ（最小起订量）
        """
        
        suppliers = []
        
        # 1. 1688搜索
        suppliers_1688 = await self._search_1688(product_keywords, filters)
        suppliers.extend(suppliers_1688)
        
        # 2. 阿里国际站搜索
        suppliers_alibaba = await self._search_alibaba(product_keywords, filters)
        suppliers.extend(suppliers_alibaba)
        
        return suppliers
    
    async def analyze_supplier(
        self,
        supplier_id: str
    ) -> Dict:
        """
        AI智能分析供应商
        
        分析维度：
        - 基本信息（成立年限/规模）
        - 产品分析（品类/价格）
        - 证书验证（ISO/FDA/CE）
        - 客户评价分析
        - 交易记录
        - 风险评分（AI计算）
        """
        
        # 抓取供应商详情
        details = await self._scrape_supplier_details(supplier_id)
        
        # AI评分
        score = await self._calculate_ai_score(details)
        
        return {
            "supplier_id": supplier_id,
            "score": score,
            "analysis": details,
            "recommendation": "推荐" if score > 80 else "谨慎"
        }
```

### **Day 3: 供应商AI分析引擎**

```python
# src/agents/supplier_analyst.py

async def compare_suppliers(
    suppliers: List[Dict]
) -> ComparisonReport:
    """
    生成供应商对比报告
    
    输出：
    - 对比矩阵表格
    - 雷达图对比
    - AI推荐
    - PDF报告
    """
    pass
```

### **Day 4: 企查查背景调查**

```python
# plugins/company_verification/plugin.py

async def verify_company(
    company_name: str
) -> CompanyReport:
    """
    企业背景调查
    
    查询：
    - 工商信息
    - 司法风险
    - 股东结构
    - 舆情分析
    """
    pass
```

### **Day 5: 微信企业号插件**

```python
# plugins/wechat_work/plugin.py

class WeChatWorkPlugin:
    """微信企业号客户管理"""
    
    async def send_mass_message(
        self,
        customers: List[str],
        content: str
    ):
        """群发消息"""
        pass
```

### **Day 6-7: 客户分析报告**

```python
# src/reports/customer_analysis.py

async def generate_customer_report(
    customer_id: str
) -> Report:
    """
    生成客户分析报告
    
    内容：
    1. 客户画像
    2. 商机评分（AI预测）
    3. 销售漏斗分析
    4. ROI分析
    
    输出格式：
    - PDF报告
    - PPT演示
    """
    pass
```

### **Day 8: 供应商对比报告**

```python
async def generate_supplier_comparison(
    supplier_ids: List[str]
) -> Report:
    """
    供应商对比报告
    
    对比维度：
    - 价格/质量/交期/风险
    - 雷达图
    - AI推荐
    """
    pass
```

### **Day 9: 业务周报/月报**

```python
async def generate_weekly_report() -> Report:
    """
    每周一自动生成周报
    
    内容：
    - 销售数据
    - 供应商数据
    - AI活动摘要
    - 风险预警
    - 下周计划
    """
    pass
```

---

## 🎉 Week 21-22 交付物总结

### **10大核心插件**

| # | 插件名称 | 核心价值 | 节省时间 |
|---|---------|---------|---------|
| 1 | LinkedIn销售助手 | 自动开发客户 | 4-5小时/天 |
| 2 | 邮件营销引擎 | 批量获客 | 3-4小时/天 |
| 3 | WhatsApp Business | 即时沟通 | 1-2小时/天 |
| 4 | 1688供应商搜索 | 智能找供应商 | 2-3小时/次 |
| 5 | 供应商AI分析 | 数据驱动决策 | 1-2小时/次 |
| 6 | 企查查背景调查 | 风险控制 | 30分钟/次 |
| 7 | 微信企业号 | 国内沟通 | 1小时/天 |
| 8 | 客户分析报告 | 商机洞察 | 2小时/周 |
| 9 | 供应商对比报告 | 采购优化 | 1小时/次 |
| 10 | 自动周报/月报 | 业务总结 | 3小时/周 |

**总节省时间：每天6小时** ⭐⭐⭐

---

## 💰 ROI分析

```
开发成本：14天 × ¥350/小时 × 8小时 = ¥39,200

每月节省：
- 时间节省：6小时/天 × 22天 = 132小时/月
- 按¥350/小时计算：132 × ¥350 = ¥46,200/月

投资回收期：¥39,200 / ¥46,200 = 0.85个月（25天）

12个月ROI：(¥46,200 × 12 - ¥39,200) / ¥39,200 = 1315% ⭐⭐⭐

这是v5.3最有价值的2周！
```

---

**Week 21-22完成后，你的外贸业务将彻底改变！** 🚀
