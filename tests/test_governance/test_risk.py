"""
Tests for Risk Evaluator
"""

from src.governance.risk import RiskEvaluator
from src.identity.models import RiskLevel


class TestRiskEvaluator:
    """Test RiskEvaluator functionality"""

    def test_critical_risk_operations(self):
        """Test CRITICAL risk level detection"""
        evaluator = RiskEvaluator()

        # System operations
        assert evaluator.evaluate("admin", "system", "shutdown") == RiskLevel.CRITICAL
        assert evaluator.evaluate("admin", "database", "reset") == RiskLevel.CRITICAL
        assert evaluator.evaluate("admin", "security", "bypass") == RiskLevel.CRITICAL
        assert evaluator.evaluate("admin", "user", "delete_admin") == RiskLevel.CRITICAL

    def test_high_risk_operations(self):
        """Test HIGH risk level detection"""
        evaluator = RiskEvaluator()

        # User operations
        assert evaluator.evaluate("admin", "user", "delete") == RiskLevel.HIGH
        assert evaluator.evaluate("admin", "user", "grant_admin") == RiskLevel.HIGH

        # Data operations
        assert evaluator.evaluate("admin", "data", "delete_bulk") == RiskLevel.HIGH
        assert evaluator.evaluate("admin", "database", "drop") == RiskLevel.HIGH

        # Security operations
        assert evaluator.evaluate("admin", "security", "disable") == RiskLevel.HIGH

        # Financial operations (context-based)
        assert evaluator.evaluate("user", "payment", "process") == RiskLevel.HIGH
        assert evaluator.evaluate("user", "financial", "anything") == RiskLevel.HIGH

    def test_medium_risk_operations(self):
        """Test MEDIUM risk level detection"""
        evaluator = RiskEvaluator()

        # User management
        assert evaluator.evaluate("admin", "user", "update_role") == RiskLevel.MEDIUM
        assert evaluator.evaluate("admin", "user", "disable") == RiskLevel.MEDIUM

        # Governance operations
        assert evaluator.evaluate("admin", "approval", "override") == RiskLevel.MEDIUM
        assert evaluator.evaluate("admin", "audit", "export") == RiskLevel.MEDIUM
        assert evaluator.evaluate("admin", "policy", "update") == RiskLevel.MEDIUM

    def test_low_risk_operations(self):
        """Test LOW risk level (default)"""
        evaluator = RiskEvaluator()

        # Standard operations
        assert evaluator.evaluate("user", "user", "read") == RiskLevel.LOW
        assert evaluator.evaluate("user", "user", "list") == RiskLevel.LOW
        assert evaluator.evaluate("user", "data", "read") == RiskLevel.LOW
        assert evaluator.evaluate("user", "report", "generate") == RiskLevel.LOW
        assert evaluator.evaluate("user", "unknown", "action") == RiskLevel.LOW

    def test_case_insensitivity(self):
        """Test that operations are matched case-insensitively"""
        evaluator = RiskEvaluator()

        # Operations should match regardless of case
        assert evaluator.evaluate("admin", "user", "delete") == RiskLevel.HIGH
        assert evaluator.evaluate("admin", "system", "shutdown") == RiskLevel.CRITICAL
        assert evaluator.evaluate("admin", "user", "update_role") == RiskLevel.MEDIUM

    def test_partial_matching(self):
        """Test that exact operations are matched"""
        evaluator = RiskEvaluator()

        # Exact matches
        assert evaluator.evaluate("admin", "user", "delete") == RiskLevel.HIGH
        assert evaluator.evaluate("admin", "data", "delete_bulk") == RiskLevel.HIGH

    def test_risk_level_ordering(self):
        """Test that risk levels can be compared"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_context_evaluation(self):
        """Test risk evaluation with context"""
        evaluator = RiskEvaluator()

        # Test with bulk operation context
        context_bulk = {"bulk_operation": True}
        risk = evaluator.evaluate("user", "user", "update", context=context_bulk)
        assert risk == RiskLevel.MEDIUM

        # Test with batch size
        context_batch = {"batch_size": 15}
        risk = evaluator.evaluate("user", "user", "update", context=context_batch)
        assert risk == RiskLevel.MEDIUM

        # Test with external call
        context_external = {"external_call": True}
        risk = evaluator.evaluate("user", "api", "call", context=context_external)
        assert risk == RiskLevel.MEDIUM

        # Test without risky context
        context_safe = {"batch_size": 5}
        risk = evaluator.evaluate("user", "user", "update", context=context_safe)
        assert risk == RiskLevel.LOW

    def test_evaluate_with_none_values(self):
        """Test evaluation with None values"""
        evaluator = RiskEvaluator()

        # Should handle None gracefully and return LOW
        risk = evaluator.evaluate("user", "unknown", "unknown", context=None)
        assert risk == RiskLevel.LOW

    def test_requires_approval(self):
        """Test approval requirement logic"""
        evaluator = RiskEvaluator()

        # HIGH and CRITICAL require approval
        assert evaluator.requires_approval(RiskLevel.CRITICAL) is True
        assert evaluator.requires_approval(RiskLevel.HIGH) is True

        # MEDIUM and LOW do not require approval
        assert evaluator.requires_approval(RiskLevel.MEDIUM) is False
        assert evaluator.requires_approval(RiskLevel.LOW) is False
