"""P0-7: 长时 workflow 阻塞风险保护验收。

验收点：
1. Settings.workflow_worker_mode ∈ {inline, background}，非法值被校验拒绝。
2. Settings.workflow_total_timeout_seconds / workflow_max_steps 默认值合理。
3. WorkflowExecutor.__init__ 读取 Settings，记录 worker_mode + 启动 warning（inline 模式）。
4. WorkflowExecutor 暴露三个新增内部方法：_run_workflow_to_completion /
   _run_all_steps_with_limits / _safe_persist_and_log_failure。
5. _run_all_steps_with_limits 超过 workflow_max_steps 时报错（fail-closed）。
"""
from __future__ import annotations

import os
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest


def _ensure_src():
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def test_settings_workflow_fields_defaults_and_validation():
    _ensure_src()
    from src.core.config import Settings

    s = Settings(_env_file=None)
    assert s.workflow_worker_mode == "inline"
    assert s.workflow_total_timeout_seconds == 1800
    assert s.workflow_max_steps == 500

    # background 合法
    os.environ["WORKFLOW_WORKER_MODE"] = "background"
    try:
        s2 = Settings(_env_file=None)
        assert s2.workflow_worker_mode == "background"
    finally:
        os.environ.pop("WORKFLOW_WORKER_MODE", None)

    # 非法值被拒绝
    with pytest.raises(Exception):
        Settings(workflow_worker_mode="celery_worker", _env_file=None)


def test_executor_reads_settings_and_exposes_new_methods():
    _ensure_src()
    from src.workflow.executor import (
        WorkflowExecutor,
        WORKER_MODE_INLINE,
    )

    ex = WorkflowExecutor()
    assert ex._worker_mode == WORKER_MODE_INLINE
    assert ex._total_timeout_s >= 60  # 至少 1min
    assert ex._max_steps >= 50
    for m in (
        "_run_workflow_to_completion",
        "_run_all_steps_with_limits",
        "_safe_persist_and_log_failure",
    ):
        assert hasattr(ex, m) and callable(getattr(ex, m)), f"missing method {m}"


@pytest.mark.asyncio
async def test_run_all_steps_exceeding_max_steps_fails_closed():
    """步数上限必须 fail-closed：超限抛 RuntimeError，不继续执行。"""
    _ensure_src()
    from src.workflow.executor import WorkflowExecutor

    ex = WorkflowExecutor()
    ex._max_steps = 2  # 强制很小的上限

    # 用一个"假装"的 3-step workflow，把 step 执行分支直接跳过（通过替换
    # _execute_step 为 no-op 避免真实 DB 依赖）。这样可以精准测试步数计数器。
    async def _fake_step(step, execution, user):
        return f"result-{step.step_id}"

    # 替换实例方法
    original = ex._execute_step
    ex._execute_step = _fake_step  # type: ignore[assignment]
    try:
        wf = types.SimpleNamespace(
            workflow_id="wf-x",
            name="wf",
            version="1",
            steps=[
                types.SimpleNamespace(step_id=f"s{i}", name=f"s{i}", step_type="TASK")
                for i in range(3)
            ],
        )
        execution = types.SimpleNamespace(
            execution_id=uuid4(),
            workflow_id="wf-x",
            started_by=0,
            variables={},
            metadata={},
            status=None,
            started_at=datetime.now(UTC),
            completed_at=None,
            result=None,
            error=None,
            step_results={},
        )
        user = types.SimpleNamespace(id=0, email="t@t")

        with pytest.raises(RuntimeError) as excinfo:
            await ex._run_all_steps_with_limits(wf, execution, user)

        msg = str(excinfo.value).lower()
        assert "step" in msg or "limit" in msg or "exceeded" in msg
        # 检查计数器确实达到上限
        assert ex._step_counter >= ex._max_steps
        print(f"step limit enforced at counter={ex._step_counter}: {excinfo.value}")
    finally:
        ex._execute_step = original  # type: ignore[assignment]
