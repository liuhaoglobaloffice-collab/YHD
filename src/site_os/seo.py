"""
S4 独立站 + SEO - SEO 引擎

提供关键词分析、内容优化（AI 生成建议）、排名跟踪。
优先调用 LLM 生成内容建议，未配置时回退规则模板。
"""

import json
import logging
import os
import random
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SEOEngine:
    """SEO 引擎"""

    # 示例关键词数据（Mock；真实可接 Google Keyword Planner / GSC）
    KEYWORD_SAMPLES = [
        {"keyword": "custom led light manufacturer", "volume": 6600, "difficulty": 32},
        {"keyword": "wholesale bluetooth earphones china", "volume": 4400, "difficulty": 28},
        {"keyword": "solar panel supplier", "volume": 8100, "difficulty": 41},
        {"keyword": "hardware oem manufacturer", "volume": 3600, "difficulty": 25},
        {"keyword": "oem consumer electronics", "volume": 2900, "difficulty": 22},
    ]

    BLOG_TEMPLATES = {
        "default": {
            "title": "{keyword}: The Complete Buying Guide for 2026",
            "outline": [
                "1. What Is {keyword}? An Overview",
                "2. Key Factors to Consider When Choosing a Supplier",
                "3. How to Evaluate Quality and Price",
                "4. OEM/ODM Options Explained",
                "5. Shipping, Lead Times and MOQ",
                "6. FAQ",
            ],
        },
        "led": {
            "title": "How to Choose a Reliable {keyword} in 2026",
            "outline": [
                "1. Understanding {keyword} Market Trends",
                "2. Certifications to Look For (CE/UL/ROHS)",
                "3. Comparing Manufacturers: Quality vs Price",
                "4. Customization & Logo Options",
                "5. Getting the Best Price & MOQ",
                "6. FAQ",
            ],
        },
    }

    async def analyze_keywords(
        self, base_keywords: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """关键词分析与扩展。"""
        if base_keywords:
            results = []
            for kw in base_keywords:
                volume = random.randint(1000, 9000)
                difficulty = random.randint(15, 55)
                results.append(
                    {
                        "keyword": kw,
                        "volume": volume,
                        "difficulty": difficulty,
                        "opportunity": round(
                            volume * (100 - difficulty) / 10000, 1
                        ),
                        "suggestions": [
                            f"{kw} factory",
                            f"{kw} wholesale",
                            f"{kw} oem supplier",
                            f"buy {kw} online",
                            f"top {kw} companies",
                        ],
                    }
                )
                if len(results) >= limit:
                    break
            return results

        return [
            {
                "keyword": s["keyword"],
                "volume": s["volume"],
                "difficulty": s["difficulty"],
                "opportunity": round(s["volume"] * (100 - s["difficulty"]) / 10000, 1),
                "suggestions": [
                    f"{s['keyword']} factory",
                    f"{s['keyword']} wholesale",
                    f"buy {s['keyword']} online",
                ],
            }
            for s in self.KEYWORD_SAMPLES[:limit]
        ]

    async def generate_content(
        self, keyword: str, site_name: Optional[str] = None, content_type: str = "blog"
    ) -> Dict[str, Any]:
        """生成 SEO 内容建议（AI 或规则模板）。"""
        try:
            return await self._generate_with_llm(keyword, site_name, content_type)
        except Exception as e:  # noqa: BLE001
            logger.warning("seo_llm_failed_falling_back error=%s", str(e))
            return self._generate_mock(keyword, site_name, content_type)

    async def _generate_with_llm(
        self, keyword: str, site_name: Optional[str], content_type: str
    ) -> Dict[str, Any]:
        from src.ai.gateway import get_gateway
        from src.ai.providers import ProviderType

        provider_str = os.getenv("LLM_PROVIDER", "mock").lower().strip()
        if provider_str == "openai":
            provider = ProviderType.OPENAI
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        elif provider_str == "ollama":
            provider = ProviderType.OLLAMA
            model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
        else:
            raise RuntimeError("LLM 未配置")

        prompt = (
            "你是外贸独立站 SEO 内容专家。请围绕关键词生成一篇优质英文博客文章方案。\n"
            f"关键词：{keyword}\n"
            f"站点名称：{site_name or 'our store'}\n"
            f"内容类型：{content_type}\n\n"
            "只输出一个 JSON 对象："
            '{"title": 文章标题, "slug": 建议URL别名, "meta_description": 160字符内, '
            '"outline": ["段落大纲1", ...], "tags": ["标签1", ...], '
            '"content": 完整文章正文（Markdown，600词以上）, "search_intent": 搜索意图}'
        )
        gateway = get_gateway()
        response = await gateway.complete(
            provider=provider,
            model_id=model,
            messages=[{"role": "user", "content": prompt}],
            trace_id=uuid4(),
            temperature=0.4,
            max_tokens=3000,
        )
        data = self._parse_json(response.content)
        return {
            "keyword": keyword,
            "title": data.get("title"),
            "suggested_slug": data.get("slug"),
            "meta_description": data.get("meta_description"),
            "outline": data.get("outline", []),
            "tags": data.get("tags", []),
            "content": data.get("content"),
            "search_intent": data.get("search_intent"),
            "method": "ai",
        }

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM 输出解析失败: {e}")

    def _generate_mock(
        self, keyword: str, site_name: Optional[str], content_type: str
    ) -> Dict[str, Any]:
        """规则模板生成内容建议。"""
        kw_lower = keyword.lower()
        template_key = "led" if "led" in kw_lower or "light" in kw_lower else "default"
        tpl = self.BLOG_TEMPLATES[template_key]

        title = tpl["title"].replace("{keyword}", keyword)
        outline = "\n".join(
            line.replace("{keyword}", keyword) for line in tpl["outline"]
        )
        slug = keyword.lower().replace(" ", "-").replace("/", "-").strip("-")[:60]
        meta_desc = f"Find the best {keyword} suppliers. Compare quality, prices, MOQ and lead times to make the right sourcing decision for your business."

        content = (
            f"# {title}\n\n"
            f"Are you looking for a reliable {keyword} supplier? You're in the right place. "
            f"This guide helps you source high-quality {keyword} products at competitive prices.\n\n"
            f"## Why Choose {site_name or 'Our Store'}\n\n"
            f"We partner with vetted manufacturers to deliver consistent quality and on-time delivery."
            f" Our team handles everything from OEM customization to logistics.\n\n"
            f"## Key Buying Factors\n\n"
            f"- **Quality**: Certified factories with ISO9001 and strict QC processes\n"
            f"- **Price**: Competitive pricing with volume discounts\n"
            f"- **MOQ**: Flexible minimum order quantities\n"
            f"- **Lead Time**: Fast production and shipping\n\n"
            f"## How to Order\n\n"
            f"1. Contact us with your requirements\n"
            f"2. Receive a customized quote within 24 hours\n"
            f"3. Approve samples and start mass production\n\n"
            f"## FAQ\n\n"
            f"**Q: Can you do OEM/ODM?** Yes, we support full customization.\n"
            f"**Q: What is your MOQ?** It depends on the product; contact us for details.\n\n"
            f"## Get a Quote Today\n\n"
            f"Contact us now to get the best {keyword} pricing for your business."
        )

        return {
            "keyword": keyword,
            "title": title,
            "suggested_slug": slug,
            "meta_description": meta_desc,
            "outline": outline.split("\n"),
            "tags": [keyword, "wholesale", "supplier", "manufacturer"],
            "content": content,
            "search_intent": "Commercial search - buyers looking for suppliers",
            "method": "mock",
        }

    async def track_rankings(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """跟踪关键词排名（Mock：返回模拟排名；真实可接 GSC/SERP API）。"""
        results = []
        for kw in keywords:
            rank = random.choice([None, 3, 8, 15, 22, 34, 47, 61, 78])
            volume = random.randint(1000, 9000)
            prev = random.choice([None, 5, 12, 18, 30, 40, 55, 70])
            trend = "new"
            if rank and prev:
                if rank < prev:
                    trend = "up"
                elif rank > prev:
                    trend = "down"
                else:
                    trend = "stable"
            results.append(
                {
                    "keyword": kw,
                    "rank": rank,
                    "previous_rank": prev,
                    "trend": trend,
                    "search_volume": volume,
                    "url": f"/blog/{kw.lower().replace(' ', '-')}",
                    "checked_at": datetime.now(UTC).isoformat(),
                }
            )
        return results