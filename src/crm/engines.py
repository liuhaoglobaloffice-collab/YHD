"""
S3 自动获客 + 供应商分析 - 获客引擎

包含三路线索挖掘：社媒（social）、谷歌搜索（google）、海关数据（customs），
以及海关数据 Provider 与国内供应商发现引擎。
未配置真实数据源时自动回退到 Mock 数据（开发模式）。
"""

import logging
import os
import random
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class LeadAcquisitionEngine:
    """自动获客引擎：从多个数据源挖掘潜在客户线索。"""

    # 社媒线索示例
    SOCIAL_SAMPLE = [
        {
            "name": "John Miller",
            "company": "Miller Imports LLC",
            "country": "美国",
            "city": "Los Angeles",
            "industry": "家居用品",
            "email": "john@millerimports.com",
            "phone": "+1 213 555 0101",
            "linkedin": "linkedin.com/in/johnmiller",
            "product_interest": "LED 灯具",
            "score": 82,
        },
        {
            "name": "Sarah Chen",
            "company": "BrightPath Trading",
            "country": "加拿大",
            "city": "Toronto",
            "industry": "消费电子",
            "email": "sarah@brightpath.ca",
            "whatsapp": "+1 416 555 0102",
            "linkedin": "linkedin.com/in/sarahchen",
            "product_interest": "蓝牙耳机",
            "score": 76,
        },
        {
            "name": "Miguel Rodriguez",
            "company": "Rodriguez Distribución",
            "country": "墨西哥",
            "city": "Monterrey",
            "industry": "五金建材",
            "email": "miguel@rodriguezdist.com",
            "whatsapp": "+52 81 555 0103",
            "product_interest": "五金件",
            "score": 68,
        },
    ]

    # 谷歌搜索线索示例
    GOOGLE_SAMPLE = [
        {
            "name": "Anna Kowalski",
            "company": "Kowalski Home & Garden",
            "country": "波兰",
            "city": "Warsaw",
            "industry": "户外用品",
            "email": "anna@kowalskihome.pl",
            "website": "kowalskihome.pl",
            "product_interest": "太阳能板",
            "score": 74,
        },
        {
            "name": "David Osei",
            "company": "Osei Hardware Ltd",
            "country": "加纳",
            "city": "Accra",
            "industry": "五金建材",
            "email": "david@oseihardware.com",
            "whatsapp": "+233 20 555 0104",
            "product_interest": "电动工具",
            "score": 71,
        },
        {
            "name": "Elena Petrova",
            "company": "Petrova Trade Group",
            "country": "俄罗斯",
            "city": "Moscow",
            "industry": "照明",
            "email": "elena@petrovatrade.ru",
            "website": "petrovatrade.ru",
            "product_interest": "LED 灯具",
            "score": 66,
        },
    ]

    # 海关线索示例（进口商）
    CUSTOMS_SAMPLE = [
        {
            "name": "Robert Tan",
            "company": "Tan Pacific Import Co.",
            "country": "新加坡",
            "city": "Singapore",
            "industry": "电子",
            "email": "robert@tanpacific.sg",
            "phone": "+65 6555 0105",
            "product_interest": "电子元件",
            "score": 79,
        },
        {
            "name": "Luis Fernandez",
            "company": "Fernandez Global Buyers",
            "country": "西班牙",
            "city": "Barcelona",
            "industry": "照明",
            "email": "luis@fernandezbuyers.es",
            "whatsapp": "+34 655 555 0106",
            "product_interest": "LED 灯具",
            "score": 73,
        },
        {
            "name": "Ahmed Hassan",
            "company": "Hassan Trading FZE",
            "country": "阿联酋",
            "city": "Dubai",
            "industry": "五金建材",
            "email": "ahmed@hassantrading.ae",
            "whatsapp": "+971 50 555 0107",
            "product_interest": "卫浴五金",
            "score": 69,
        },
    ]

    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "")
        self.google_cx = os.getenv("GOOGLE_SEARCH_CX", "")

    async def run(
        self,
        sources: List[str],
        keywords: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        运行获客引擎。

        Args:
            sources: ["social", "google", "customs"] 中的子集
            keywords: 搜索关键词
            limit: 每源返回数量上限

        Returns:
            {"leads": [...], "stats": {"social": n, "google": n, "customs": n}}
        """
        keywords = keywords or ["LED lighting", "hardware wholesale", "consumer electronics"]
        all_leads: List[Dict[str, Any]] = []
        stats: Dict[str, int] = {}

        if "social" in sources:
            social = self._social_leads(keywords, limit)
            all_leads.extend(social)
            stats["social"] = len(social)

        if "google" in sources:
            google = await self._google_leads(keywords, limit)
            all_leads.extend(google)
            stats["google"] = len(google)

        if "customs" in sources:
            customs = self._customs_leads(keywords, limit)
            all_leads.extend(customs)
            stats["customs"] = len(customs)

        return {"leads": all_leads, "stats": stats}

    def _social_leads(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """社媒线索（Mock：返回示例；真实可接 LinkedIn/Facebook API）。"""
        leads = [dict(l) for l in self.SOCIAL_SAMPLE[:limit]]
        for l in leads:
            l["source"] = "social"
            l["source_detail"] = random.choice(keywords)
        return leads

    async def _google_leads(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """谷歌搜索线索。配置了 Custom Search API 时走真实接口，否则 Mock。"""
        if self.google_api_key and self.google_cx:
            try:
                return await self._google_real(keywords, limit)
            except Exception as e:  # noqa: BLE001
                logger.warning("google_search_failed_falling_back error=%s", str(e))
        leads = [dict(l) for l in self.GOOGLE_SAMPLE[:limit]]
        for l in leads:
            l["source"] = "google"
            l["source_detail"] = random.choice(keywords)
        return leads

    async def _google_real(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """调用 Google Custom Search API 提取公司线索（简化版）。"""
        results: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for kw in keywords[:2]:
                resp = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.google_cx,
                        "q": f"{kw} wholesale import company",
                        "num": min(limit, 10),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("items", []):
                    results.append(
                        {
                            "name": item.get("title", "")[:60],
                            "company": item.get("title", ""),
                            "country": "",
                            "website": item.get("link", ""),
                            "source": "google",
                            "source_detail": kw,
                            "score": 60,
                        }
                    )
        return results

    def _customs_leads(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """海关数据线索（Mock：返回示例进口商）。"""
        leads = [dict(l) for l in self.CUSTOMS_SAMPLE[:limit]]
        for l in leads:
            l["source"] = "customs"
            l["source_detail"] = random.choice(keywords)
        return leads


class CustomsDataProvider:
    """海关进出口数据查询。"""

    # 示例海关记录
    SAMPLE = [
        {
            "hs_code": "940542",
            "product": "LED 灯串",
            "product_desc": "LED 室内装饰灯串",
            "importer_name": "Tan Pacific Import Co.",
            "importer_country": "新加坡",
            "exporter_name": "中山市某某灯饰",
            "exporter_country": "中国",
            "quantity": 5000,
            "unit": "件",
            "value": 25000.0,
            "trade_date": "2026-07-15",
        },
        {
            "hs_code": "851830",
            "product": "蓝牙耳机",
            "product_desc": "TWS 无线蓝牙耳机",
            "importer_name": "BrightPath Trading",
            "importer_country": "加拿大",
            "exporter_name": "深圳市某某电子",
            "exporter_country": "中国",
            "quantity": 2000,
            "unit": "副",
            "value": 18000.0,
            "trade_date": "2026-06-28",
        },
        {
            "hs_code": "732690",
            "product": "五金件",
            "product_desc": "不锈钢五金配件",
            "importer_name": "Hassan Trading FZE",
            "importer_country": "阿联酋",
            "exporter_name": "东莞市某某五金",
            "exporter_country": "中国",
            "quantity": 8000,
            "unit": "公斤",
            "value": 15000.0,
            "trade_date": "2026-08-02",
        },
    ]

    def __init__(self):
        self.api_url = os.getenv("CUSTOMS_API_URL", "")

    async def search(
        self,
        product: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """查询海关数据。"""
        if self.api_url:
            try:
                return await self._search_real(product, country, limit)
            except Exception as e:  # noqa: BLE001
                logger.warning("customs_api_failed_falling_back error=%s", str(e))
        return self._search_mock(product, country, limit)

    async def _search_real(
        self, product: Optional[str], country: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                self.api_url,
                params={
                    "product": product or "",
                    "country": country or "",
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return data if isinstance(data, list) else data.get("records", [])

    def _search_mock(
        self, product: Optional[str], country: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        records = []
        for r in self.SAMPLE:
            if product and product.lower() not in r["product"].lower():
                continue
            if country and country not in r["importer_country"] and country not in r["exporter_country"]:
                continue
            records.append(dict(r))
        return records[:limit]


class SupplierDiscoveryEngine:
    """国内供应商发现引擎。"""

    # 示例国内供应商
    SAMPLE = [
        {
            "name": "中山市某某灯饰有限公司",
            "province": "广东",
            "city": "中山",
            "product_category": "LED 灯具",
            "phone": "0760-8888 0001",
            "website": "example-lighting.cn",
        },
        {
            "name": "深圳市某某电子科技有限公司",
            "province": "广东",
            "city": "深圳",
            "product_category": "消费电子",
            "phone": "0755-8888 0002",
            "website": "example-electronics.cn",
        },
        {
            "name": "东莞市某某五金制造有限公司",
            "province": "广东",
            "city": "东莞",
            "product_category": "五金件",
            "phone": "0769-8888 0003",
            "website": "example-hardware.cn",
        },
    ]

    async def discover(
        self, product: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """发现国内供应商（Mock：返回示例）。"""
        results = []
        for s in self.SAMPLE:
            if product and product.lower() not in s["product_category"].lower():
                continue
            results.append(dict(s))
        return results[:limit]
