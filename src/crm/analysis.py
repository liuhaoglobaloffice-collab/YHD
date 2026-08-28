"""
S3 自动获客 + 供应商分析 - 供应商分析服务

生成供应商多维分析报告（风险 / 价格 / 产能），
优先调用 LLM（Ollama/OpenAI）输出结构化分析，不可用时回退到规则+模板分析。
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crm.models import SupplierAnalysisReport

logger = logging.getLogger(__name__)


class SupplierAnalysisService:
    """供应商分析服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_report(
        self,
        supplier_name: str,
        product_category: Optional[str] = None,
        supplier_data: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None,
        tenant_id: Optional[str] = None,
        supplier_id: Optional[int] = None,
    ) -> SupplierAnalysisReport:
        """生成并保存供应商分析报告。"""
        data = supplier_data or {}

        try:
            result = await self._analyze_with_llm(supplier_name, product_category, data)
            method = "ai"
        except Exception as e:  # noqa: BLE001
            logger.warning("supplier_analysis_llm_failed_falling_back error=%s", str(e))
            result = self._analyze_mock(supplier_name, product_category, data)
            method = "mock"

        report = SupplierAnalysisReport(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            product_category=product_category,
            risk_level=result.get("risk_level"),
            risk_score=result.get("risk_score"),
            risk_summary=result.get("risk_summary"),
            price_level=result.get("price_level"),
            price_score=result.get("price_score"),
            price_summary=result.get("price_summary"),
            capacity_level=result.get("capacity_level"),
            capacity_score=result.get("capacity_score"),
            overall_score=result.get("overall_score"),
            overall_level=result.get("overall_level"),
            report=result.get("report"),
            recommendations=result.get("recommendations", []),
            analysis_method=method,
            created_by=created_by,
            tenant_id=tenant_id,
        )
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_latest(self, supplier_id: int, user_ids: Optional[Set[int]] = None) -> Optional[SupplierAnalysisReport]:
        stmt = (
            select(SupplierAnalysisReport)
            .where(SupplierAnalysisReport.supplier_id == supplier_id)
            .order_by(SupplierAnalysisReport.created_at.desc())
            .limit(1)
        )
        if user_ids:
            stmt = stmt.where(SupplierAnalysisReport.created_by.in_(list(user_ids)))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_reports(
        self, limit: int = 50, supplier_id: Optional[int] = None, user_ids: Optional[Set[int]] = None
    ) -> List[SupplierAnalysisReport]:
        stmt = select(SupplierAnalysisReport)
        if user_ids:
            stmt = stmt.where(SupplierAnalysisReport.created_by.in_(list(user_ids)))
        stmt = stmt.order_by(
            SupplierAnalysisReport.created_at.desc()
        )
        if supplier_id:
            stmt = stmt.where(SupplierAnalysisReport.supplier_id == supplier_id)
        stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    # ==================== LLM 分析 ====================

    async def _analyze_with_llm(
        self, name: str, category: Optional[str], data: Dict[str, Any]
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

        context = {
            "name": name,
            "product_category": category,
            "country": data.get("country"),
            "province": data.get("province"),
            "city": data.get("city"),
            "business_type": data.get("business_type"),
            "registered_capital": data.get("registered_capital"),
            "employee_count": data.get("employee_count"),
            "annual_revenue": data.get("annual_revenue"),
            "established_date": data.get("established_date"),
            "has_iso9001": data.get("has_iso9001"),
            "has_export_license": data.get("has_export_license"),
            "cooperation_years": data.get("cooperation_years"),
            "total_orders": data.get("total_orders"),
            "risk_score": data.get("risk_score"),
            "status": data.get("status"),
        }
        prompt = (
            "你是供应链分析专家。请分析以下供应商，从【风险】【价格】【产能】三个维度评估。\n"
            f"供应商信息：{json.dumps(context, ensure_ascii=False)}\n\n"
            "只输出一个 JSON 对象，不要包含其他内容。字段："
            '{"risk_level": "低/中/高", "risk_score": 0-100, "risk_summary": "...", '
            '"price_level": "高/中/低", "price_score": 0-100, "price_summary": "...", '
            '"capacity_level": "高/中/低", "capacity_score": 0-100, "capacity_summary": "...", '
            '"overall_score": 0-100, "overall_level": "A/B/C/D", '
            '"report": "完整 Markdown 分析报告", '
            '"recommendations": ["建议1", "建议2", "建议3"]}'
        )
        gateway = get_gateway()
        response = await gateway.complete(
            provider=provider,
            model_id=model,
            messages=[{"role": "user", "content": prompt}],
            trace_id=uuid4(),
            temperature=0.3,
            max_tokens=3000,
        )
        return self._parse_llm_json(response.content)

    @staticmethod
    def _parse_llm_json(content: str) -> Dict[str, Any]:
        """解析 LLM 输出的 JSON（容忍代码块包裹）。"""
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

    # ==================== Mock 分析（规则 + 模板） ====================

    def _analyze_mock(
        self, name: str, category: Optional[str], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于规则与供应商数据的启发式分析。"""
        # 风险评分（越低越好）
        risk = 50
        if data.get("is_verified"):
            risk -= 15
        if data.get("has_iso9001"):
            risk -= 10
        if data.get("has_export_license"):
            risk -= 5
        if data.get("cooperation_years") and data["cooperation_years"] >= 3:
            risk -= 10
        if data.get("risk_score") is not None:
            risk = int(data["risk_score"])
        risk = max(0, min(100, risk))
        risk_level = "低" if risk < 35 else ("中" if risk < 65 else "高")

        # 价格竞争力评分（注册资本/营收越高，议价能力越强）
        price = 50
        if data.get("registered_capital"):
            cap = float(data["registered_capital"])
            if cap >= 1000000:
                price += 20
            elif cap >= 100000:
                price += 10
        if data.get("annual_revenue"):
            rev = float(data["annual_revenue"])
            if rev >= 10000000:
                price += 15
        price = max(0, min(100, price))
        price_level = "高" if price >= 70 else ("中" if price >= 45 else "低")

        # 产能评分（员工数/年限）
        capacity = 50
        if data.get("employee_count"):
            emp = int(data["employee_count"])
            if emp >= 500:
                capacity += 25
            elif emp >= 100:
                capacity += 15
            elif emp >= 20:
                capacity += 8
        if data.get("established_date"):
            try:
                year = int(str(data["established_date"])[:4])
                if datetime.now(timezone.utc).year - year >= 10:
                    capacity += 10
                elif datetime.now(timezone.utc).year - year >= 5:
                    capacity += 5
            except (ValueError, TypeError):
                pass
        capacity = max(0, min(100, capacity))
        capacity_level = "高" if capacity >= 70 else ("中" if capacity >= 45 else "低")

        overall = round(risk * 0.4 + price * 0.3 + capacity * 0.3, 1)
        overall_level = "A" if overall >= 80 else ("B" if overall >= 65 else ("C" if overall >= 50 else "D"))

        report = (
            f"## 供应商分析报告：{name}\n\n"
            f"- **产品类别**：{category or '未知'}\n"
            f"- **国家/地区**：{data.get('country') or data.get('province') or '未知'}\n"
            f"- **业务类型**：{data.get('business_type') or '未知'}\n\n"
            f"### 综合评级：{overall_level}（{overall} 分）\n\n"
            f"### 风险分析（{risk_level}，{risk} 分）\n"
            f"{self._risk_text(risk, data)}\n\n"
            f"### 价格竞争力（{price_level}，{price} 分）\n"
            f"{self._price_text(price, data)}\n\n"
            f"### 产能分析（{capacity_level}，{capacity} 分）\n"
            f"{self._capacity_text(capacity, data)}\n\n"
            "> 注：当前为规则分析模式（Mock），配置 LLM 后可生成深度 AI 分析。"
        )

        recommendations = []
        if risk >= 65:
            recommendations.append("建议实地验厂并核查资质证书，规避合规风险")
        if price >= 70:
            recommendations.append("价格竞争力强，可争取更优付款条件")
        elif price < 45:
            recommendations.append("价格偏高，建议对比 2-3 家供应商后议价")
        if capacity < 45:
            recommendations.append("产能有限，旺季需提前锁定产能或备选供应商")
        if not recommendations:
            recommendations.append("综合表现良好，可推进合作与下单")
        recommendations.append("定期复评供应商表现，跟踪价格与交付数据")

        return {
            "risk_level": risk_level,
            "risk_score": risk,
            "risk_summary": self._risk_text(risk, data),
            "price_level": price_level,
            "price_score": price,
            "price_summary": self._price_text(price, data),
            "capacity_level": capacity_level,
            "capacity_score": capacity,
            "capacity_summary": self._capacity_text(capacity, data),
            "overall_score": overall,
            "overall_level": overall_level,
            "report": report,
            "recommendations": recommendations,
        }

    @staticmethod
    def _risk_text(risk: int, data: Dict[str, Any]) -> str:
        factors = []
        if data.get("is_verified"):
            factors.append("已实地验厂")
        if data.get("has_iso9001"):
            factors.append("具备 ISO9001 认证")
        if data.get("has_export_license"):
            factors.append("具备出口资质")
        if data.get("cooperation_years") and data["cooperation_years"] >= 3:
            factors.append(f"合作 {data['cooperation_years']} 年")
        base = f"风险评分 {risk}（0-100，越低越安全）。"
        if factors:
            base += " 积极因素：" + "、".join(factors) + "。"
        return base

    @staticmethod
    def _price_text(price: int, data: Dict[str, Any]) -> str:
        parts = [f"价格竞争力评分 {price}。"]
        if data.get("registered_capital"):
            parts.append(f"注册资本 {data['registered_capital']} USD。")
        if data.get("annual_revenue"):
            parts.append(f"年营收 {data['annual_revenue']} USD。")
        return " ".join(parts)

    @staticmethod
    def _capacity_text(capacity: int, data: Dict[str, Any]) -> str:
        parts = [f"产能评分 {capacity}。"]
        if data.get("employee_count"):
            parts.append(f"员工数 {data['employee_count']}。")
        if data.get("established_date"):
            parts.append(f"成立时间 {data['established_date']}。")
        return " ".join(parts)
