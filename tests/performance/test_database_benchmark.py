"""
Database Query Performance Tests

测试数据库查询性能，发现慢查询
目标: <50ms
"""

import pytest
from sqlalchemy import text

from src.database.models import TaskModel, WorkflowModel


class TestDatabaseQueryPerformance:
    """数据库查询性能测试"""

    @pytest.mark.asyncio
    async def test_simple_select_performance(self, benchmark, test_session):
        """简单SELECT查询性能"""

        async def simple_select():
            result = await test_session.execute(text("SELECT 1"))
            return result.scalar()

        result = await benchmark.pedantic(simple_select, iterations=1000, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_user_select_by_id_performance(self, benchmark, test_session):
        """用户ID查询性能"""

        async def select_user():
            stmt = text("SELECT * FROM users WHERE id = :id")
            result = await test_session.execute(stmt, {"id": 1})
            return result.fetchone()

        result = await benchmark.pedantic(select_user, iterations=500, rounds=10)
        # 可能为None，但要测速度

    @pytest.mark.asyncio
    async def test_user_select_with_join_performance(self, benchmark, test_session):
        """用户关联查询性能"""

        async def select_user_with_role():
            stmt = text(
                """
                SELECT u.*, r.name as role_name
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE u.id = :id
            """
            )
            result = await test_session.execute(stmt, {"id": 1})
            return result.fetchone()

        result = await benchmark.pedantic(
            select_user_with_role, iterations=200, rounds=5
        )

    @pytest.mark.asyncio
    async def test_task_list_performance(self, benchmark, test_session):
        """任务列表查询性能"""

        async def list_tasks():
            stmt = text(
                """
                SELECT * FROM tasks
                WHERE status != 'deleted'
                ORDER BY created_at DESC
                LIMIT 50
            """
            )
            result = await test_session.execute(stmt)
            return result.fetchall()

        result = await benchmark.pedantic(list_tasks, iterations=200, rounds=5)

    @pytest.mark.asyncio
    async def test_workflow_complex_query_performance(self, benchmark, test_session):
        """工作流复杂查询性能"""

        async def complex_workflow_query():
            stmt = text(
                """
                SELECT w.*, 
                       COUNT(DISTINCT we.id) as execution_count,
                       AVG(we.duration_seconds) as avg_duration
                FROM workflows w
                LEFT JOIN workflow_executions we ON w.id = we.workflow_id
                WHERE w.is_active = true
                GROUP BY w.id
                LIMIT 20
            """
            )
            result = await test_session.execute(stmt)
            return result.fetchall()

        result = await benchmark.pedantic(
            complex_workflow_query, iterations=50, rounds=3
        )

    @pytest.mark.asyncio
    async def test_audit_log_query_performance(self, benchmark, test_session):
        """审计日志查询性能"""

        async def query_audit_logs():
            stmt = text(
                """
                SELECT * FROM audit_logs
                WHERE user_id = :user_id
                  AND created_at >= datetime('now', '-7 days')
                ORDER BY created_at DESC
                LIMIT 100
            """
            )
            result = await test_session.execute(stmt, {"user_id": 1})
            return result.fetchall()

        result = await benchmark.pedantic(query_audit_logs, iterations=100, rounds=5)


class TestDatabaseWritePerformance:
    """数据库写入性能测试"""

    @pytest.mark.asyncio
    async def test_single_insert_performance(self, benchmark, test_session):
        """单条插入性能"""

        async def insert_audit_log():
            stmt = text(
                """
                INSERT INTO audit_logs (user_id, action, resource_type, status)
                VALUES (:user_id, :action, :resource_type, :status)
            """
            )
            await test_session.execute(
                stmt,
                {
                    "user_id": 1,
                    "action": "test",
                    "resource_type": "benchmark",
                    "status": "success",
                },
            )
            await test_session.rollback()  # 回滚不实际插入

        await benchmark.pedantic(insert_audit_log, iterations=100, rounds=5)

    @pytest.mark.asyncio
    async def test_batch_insert_performance(self, benchmark, test_session):
        """批量插入性能"""

        async def batch_insert():
            stmt = text(
                """
                INSERT INTO audit_logs (user_id, action, resource_type, status)
                VALUES (:user_id, :action, :resource_type, :status)
            """
            )
            # 批量插入10条
            for i in range(10):
                await test_session.execute(
                    stmt,
                    {
                        "user_id": 1,
                        "action": f"test_{i}",
                        "resource_type": "benchmark",
                        "status": "success",
                    },
                )
            await test_session.rollback()

        await benchmark.pedantic(batch_insert, iterations=50, rounds=3)

    @pytest.mark.asyncio
    async def test_update_performance(self, benchmark, test_session):
        """更新性能"""

        async def update_user():
            stmt = text(
                """
                UPDATE users
                SET full_name = :name
                WHERE id = :id
            """
            )
            await test_session.execute(stmt, {"id": 1, "name": "Benchmark Test"})
            await test_session.rollback()

        await benchmark.pedantic(update_user, iterations=100, rounds=5)


class TestDatabaseIndexPerformance:
    """数据库索引性能测试"""

    @pytest.mark.asyncio
    async def test_indexed_vs_non_indexed_query(self, benchmark, test_session):
        """索引 vs 非索引查询对比"""

        # 测试有索引的查询 (id主键)
        async def indexed_query():
            stmt = text("SELECT * FROM users WHERE id = :id")
            result = await test_session.execute(stmt, {"id": 1})
            return result.fetchone()

        await benchmark.pedantic(indexed_query, iterations=500, rounds=10)

        # 注意: 非索引查询测试需要在实际数据库中进行
        # 这里只测试索引查询作为基准


# 性能目标
DATABASE_PERFORMANCE_TARGETS = {
    "simple_select": 0.001,  # 1ms
    "select_by_id": 0.005,  # 5ms
    "select_with_join": 0.010,  # 10ms
    "list_query": 0.020,  # 20ms
    "complex_query": 0.050,  # 50ms
    "single_insert": 0.010,  # 10ms
    "batch_insert": 0.050,  # 50ms
    "update": 0.010,  # 10ms
}
