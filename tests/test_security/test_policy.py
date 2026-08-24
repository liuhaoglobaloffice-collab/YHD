"""
Tests for Policy Engine (Fail Closed behavior)
"""

import os

import pytest

from src.security.policy import PolicyAction, get_policy_engine


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    os.environ.setdefault("SECRET_KEY", "test_secret_key_32_characters_min")
    os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_32_characters_min")
    yield


@pytest.mark.asyncio
async def test_unknown_resource_deny():
    """Test that unknown resources are denied (Fail Closed)"""
    policy_engine = get_policy_engine()

    decision = policy_engine.evaluate(
        resource="unknown_resource",
        action="access",
    )

    assert decision.action == PolicyAction.DENY
    assert "Unknown resource" in decision.reason


@pytest.mark.asyncio
async def test_disabled_feature_deny():
    """Test that disabled features are denied"""
    policy_engine = get_policy_engine()

    # provider_gateway is disabled by default
    decision = policy_engine.evaluate(
        resource="provider_gateway",
        action="call",
        context={"provider": "openai"},
    )

    assert decision.action == PolicyAction.DENY
    assert "disabled" in decision.reason.lower()


@pytest.mark.asyncio
async def test_empty_whitelist_deny():
    """Test that empty whitelist denies all (Fail Closed)"""
    policy_engine = get_policy_engine()

    # Enable feature but whitelist is empty
    policy_engine.update_policy(
        "provider_gateway",
        {
            "enabled": True,
            "require_approval": False,
            "allowed_providers": [],  # Empty = none allowed
        },
    )

    decision = policy_engine.evaluate(
        resource="provider_gateway",
        action="call",
        context={"provider": "openai"},
    )

    assert decision.action == PolicyAction.DENY
    assert "whitelist is empty" in decision.reason


@pytest.mark.asyncio
async def test_whitelist_allow():
    """Test that whitelisted resources are allowed"""
    policy_engine = get_policy_engine()

    # Enable feature and add to whitelist
    policy_engine.update_policy(
        "provider_gateway",
        {
            "enabled": True,
            "require_approval": False,
            "allowed_providers": ["openai", "anthropic"],
        },
    )

    decision = policy_engine.evaluate(
        resource="provider_gateway",
        action="call",
        context={"provider": "openai"},
    )

    assert decision.action == PolicyAction.ALLOW
    assert decision.is_allowed()


@pytest.mark.asyncio
async def test_not_in_whitelist_deny():
    """Test that resources not in whitelist are denied"""
    policy_engine = get_policy_engine()

    policy_engine.update_policy(
        "provider_gateway",
        {
            "enabled": True,
            "require_approval": False,
            "allowed_providers": ["openai"],
        },
    )

    decision = policy_engine.evaluate(
        resource="provider_gateway",
        action="call",
        context={"provider": "unknown_provider"},
    )

    assert decision.action == PolicyAction.DENY
    assert "not in whitelist" in decision.reason


@pytest.mark.asyncio
async def test_require_approval():
    """Test that high-risk operations require approval"""
    policy_engine = get_policy_engine()

    policy_engine.update_policy(
        "network_gateway",
        {
            "enabled": True,
            "require_approval": True,
            "allowed_domains": ["example.com"],
        },
    )

    decision = policy_engine.evaluate(
        resource="network_gateway",
        action="access",
        context={"url": "https://example.com"},
    )

    assert decision.action == PolicyAction.REQUIRE_APPROVAL
    assert decision.requires_approval()


@pytest.mark.asyncio
async def test_missing_context_deny():
    """Test that missing context is denied (Fail Closed)"""
    policy_engine = get_policy_engine()

    policy_engine.update_policy(
        "provider_gateway",
        {
            "enabled": True,
            "require_approval": False,
            "allowed_providers": ["openai"],
        },
    )

    # Missing provider in context
    decision = policy_engine.evaluate(
        resource="provider_gateway",
        action="call",
        context={},  # No provider specified
    )

    assert decision.action == PolicyAction.DENY
    assert "not specified" in decision.reason.lower()
