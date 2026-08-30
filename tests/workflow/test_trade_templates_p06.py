"""P0-6: 外贸模板 Stub 修复验收测试。

验收清单（对应 5 个 NotImplementedError）：
1. 基类 TradeWorkflowTemplate.template_id / name / description / category / build
   直接访问时不再抛异常，返回规则默认值。
2. 三个子类 + 注册表正常初始化，不再被基类 stub 抛错打断。
3. list/get_trade_template 注入 source_type（RULE_BASED 或 NOT_CONFIGURED）。
4. render_enhanced_template(llm_ctx=None) 诚实返回 NOT_CONFIGURED，不伪造 LLM 结果。
5. 未注册 template_id 走 get_trade_template 返回 NOT_CONFIGURED，不抛 ValueError。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest


def _src():
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def test_base_template_five_accessors_no_longer_raise():
    """5 个原 stub 钩子：template_id / name / description / category / build。"""
    _src()
    from src.workflow.trade_templates import (
        TradeWorkflowTemplate,
        SOURCE_RULE_BASED,
    )

    b = TradeWorkflowTemplate()
    # 以下任一在修复前会 raise NotImplementedError
    assert isinstance(b.template_id, str) and b.template_id
    assert isinstance(b.name, str) and b.name
    assert isinstance(b.description, str) and b.description
    assert isinstance(b.category, str) and b.category
    built = b.build()
    assert isinstance(built, dict)
    assert built["source_type"] == SOURCE_RULE_BASED


def test_registered_templates_are_three_and_source_typed():
    _src()
    from src.workflow.trade_templates import (
        TRADE_TEMPLATES,
        list_trade_templates,
        SOURCE_RULE_BASED,
    )

    assert set(TRADE_TEMPLATES.keys()) == {
        "customer_development",
        "supplier_procurement",
        "deal_closure",
    }
    lst = list_trade_templates()
    assert len(lst) == 3
    for tpl in lst:
        assert tpl["source_type"] == SOURCE_RULE_BASED
        assert "category_label" in tpl
        # 步骤定义不丢
        assert tpl["steps"] and all("name" in s for s in tpl["steps"])


def test_get_trade_template_unknown_id_not_configured_no_raise():
    """P0-6：未知模板不再抛 ValueError，诚实返回 NOT_CONFIGURED。"""
    _src()
    from src.workflow.trade_templates import (
        get_trade_template,
        SOURCE_NOT_CONFIGURED,
    )

    res = get_trade_template("definitely_not_a_real_template_id_xyz")
    assert res["source_type"] == SOURCE_NOT_CONFIGURED
    assert "warning" in res


@pytest.mark.asyncio
async def test_render_enhanced_llm_ctx_none_honest_not_configured():
    """LLM 上下文为空时，明确标记 NOT_CONFIGURED，不伪造 LLM 个性化。"""
    _src()
    from src.workflow.trade_templates import (
        render_enhanced_template,
        SOURCE_NOT_CONFIGURED,
    )

    r = await render_enhanced_template("customer_development", llm_ctx=None)
    assert r["source_type"] == SOURCE_NOT_CONFIGURED
    enh = r.get("enhancement") or {}
    assert enh.get("available") is False
    # 至少包含原因，可追溯
    assert isinstance(enh.get("reason"), str) and len(enh["reason"]) > 0
