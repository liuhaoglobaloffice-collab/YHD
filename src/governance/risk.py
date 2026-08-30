"""
Risk Evaluator - Determines risk level for operations
"""

from typing import Optional

import structlog

from src.identity.models import RiskLevel

logger = structlog.get_logger(__name__)


class RiskEvaluator:
    """
    Evaluates risk level for operations requiring approval

    Risk assessment based on:
    - Operation type
    - Resource type
    - Action type
    - Context
    """

    # High-risk operations
    HIGH_RISK_OPERATIONS = {
        "user:delete",
        "user:grant_admin",
        "role:delete",
        "permission:grant",
        "system:configure",
        "data:delete_bulk",
        "database:drop",
        "security:disable",
        # 外贸业务高风险操作
        "message:batch_send",       # 批量发送营销消息
        "lead:bulk_delete",         # 批量删除客户
        "customer:bulk_delete",     # 批量删除客户资料
        "supplier:bulk_delete",     # 批量删除供应商
        "ai:model_config",          # 修改AI模型配置
        "ai:api_key_manage",         # 管理API Key
        "system:core_config",       # 修改企业核心配置
        "data:export_all",          # 导出全部数据
        "finance:view",             # 查看财务数据
        "employee:bulk_delete",     # 批量删除员工
    }

    CRITICAL_RISK_OPERATIONS = {
        "system:shutdown",
        "database:reset",
        "security:bypass",
        "user:delete_admin",
    }

    MEDIUM_RISK_OPERATIONS = {
        "user:update_role",
        "user:disable",
        "approval:override",
        "audit:export",
        "policy:update",
    }

    def __init__(self):
        logger.info("risk_evaluator_initialized")

    def evaluate(
        self,
        request_type: str,
        resource: str,
        action: str,
        context: Optional[dict] = None,
    ) -> RiskLevel:
        """
        Evaluate risk level for an operation

        Args:
            request_type: Type of request
            resource: Target resource
            action: Action to perform
            context: Additional context

        Returns:
            RiskLevel enum value
        """
        operation = f"{resource}:{action}"
        context = context or {}

        # Allow pre-determined risk level from context to take precedence
        if "risk_level" in context:
            risk_from_context = context["risk_level"]
            if isinstance(risk_from_context, RiskLevel):
                return risk_from_context
            try:
                return RiskLevel(risk_from_context)
            except (ValueError, TypeError):
                pass

        # Critical risk
        if operation in self.CRITICAL_RISK_OPERATIONS:
            logger.warning(
                "critical_risk_detected",
                operation=operation,
                request_type=request_type,
            )
            return RiskLevel.CRITICAL

        # ALL delete operations are HIGH risk (Phase 2 Governance requirement)
        if action == "delete":
            logger.warning(
                "high_risk_delete_operation",
                operation=operation,
                request_type=request_type,
            )
            return RiskLevel.HIGH

        # High risk
        if operation in self.HIGH_RISK_OPERATIONS:
            logger.warning(
                "high_risk_detected",
                operation=operation,
                request_type=request_type,
            )
            return RiskLevel.HIGH

        # Medium risk
        if operation in self.MEDIUM_RISK_OPERATIONS:
            logger.info(
                "medium_risk_detected",
                operation=operation,
                request_type=request_type,
            )
            return RiskLevel.MEDIUM

        # Check for bulk operations
        if context.get("bulk_operation") or context.get("batch_size", 0) > 10:
            logger.info("medium_risk_bulk_operation", operation=operation)
            return RiskLevel.MEDIUM

        # 大批量消息发送（>100）自动升级为高风险
        if context.get("batch_size", 0) > 100 or context.get("recipient_count", 0) > 100:
            logger.warning("high_risk_large_batch_operation", operation=operation, batch_size=context.get("batch_size", 0))
            return RiskLevel.HIGH

        # Check for financial operations
        if "payment" in resource or "invoice" in resource or "financial" in resource:
            logger.info("high_risk_financial_operation", operation=operation)
            return RiskLevel.HIGH

        # Check for external operations
        if context.get("external_call") or "external" in resource:
            logger.info("medium_risk_external_operation", operation=operation)
            return RiskLevel.MEDIUM

        # Default to low risk
        logger.debug("low_risk_operation", operation=operation)
        return RiskLevel.LOW

    def requires_approval(self, risk_level: RiskLevel) -> bool:
        """
        Determine if a risk level requires approval

        Args:
            risk_level: Risk level

        Returns:
            True if approval required
        """
        requires = risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        logger.debug(
            "approval_requirement_check",
            risk_level=risk_level,
            requires_approval=requires,
        )
        return requires
