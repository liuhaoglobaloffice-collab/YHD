"""
AI collective intelligence tests - L1 to L2-L3.

Tests MemoryService agent experience store/recall with trust-based access control.
"""

import pytest
import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.knowledge.memory import MemoryService, MemoryType, Memory


def _make_service():
    session = MagicMock()
    rbac = MagicMock()
    audit = MagicMock()
    svc = MemoryService(session, rbac, audit)
    return svc


def _make_mock_model(content=None, context=None):
    m = MagicMock()
    m.id = uuid4()
    m.user_id = 0
    m.memory_type = MemoryType.LONG_TERM.value
    m.content = json.dumps(content or {})
    m.context = json.dumps(context or {})
    m.session_id = None
    m.task_id = None
    m.source = None
    m.confidence = 1.0
    m.created_at = None
    m.expires_at = None
    m.accessed_at = None
    m.access_count = 0
    m.is_active = True
    return m


@pytest.mark.asyncio
async def test_store_agent_experience():
    service = _make_service()
    service.repository = MagicMock()
    mock_model = _make_mock_model()
    service.repository.create = AsyncMock(return_value=mock_model)
    result = await service.store_agent_experience(
        employee_id=str(uuid4()),
        task_type='sales',
        result_summary='Converted lead at 15% rate',
    )
    assert result is not None
    service.repository.create.assert_called_once()


@pytest.mark.asyncio
async def test_recall_agent_experience():
    service = _make_service()
    mock_model = _make_mock_model(
        content={'key': 'sales', 'value': 'Converted lead'},
        context={'task_type': 'sales', 'shared': True},
    )
    service.repository = MagicMock()
    service.repository.list_by_type = AsyncMock(return_value=[mock_model])
    experiences = await service.recall_agent_experience(
        task_type='sales',
        limit=5,
    )
    assert len(experiences) >= 1


@pytest.mark.asyncio
async def test_low_trust_agent_denied_access():
    service = _make_service()
    mock_model = _make_mock_model()
    service.repository = MagicMock()
    service.repository.list_by_type = AsyncMock(return_value=[mock_model])
    experiences = await service.recall_agent_experience(
        task_type='sales',
        limit=5,
        requester_trust_score=0.1,
    )
    assert experiences == []


@pytest.mark.asyncio
async def test_high_trust_agent_can_access():
    service = _make_service()
    mock_model = _make_mock_model(
        content={'key': 'sales', 'value': 'Experience data'},
        context={'task_type': 'sales', 'shared': True},
    )
    service.repository = MagicMock()
    service.repository.list_by_type = AsyncMock(return_value=[mock_model])
    experiences = await service.recall_agent_experience(
        task_type='sales',
        limit=5,
        requester_trust_score=0.8,
    )
    assert len(experiences) >= 1
