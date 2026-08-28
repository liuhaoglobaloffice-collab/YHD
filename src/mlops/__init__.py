"""
Phase 4 lightweight MLOps experiment and registry primitives.

⚠️ 注意：此模块为骨架/原型实现（Phase 4 milestone placeholder）。
   - trainer.py: 训练任务为模拟执行，返回模拟指标
   - deployment.py: 没有实际部署逻辑
   - ab_testing.py: 没有真实流量路由
   真实 MLOps 闭环（训练→评估→注册→A/B测试→灰度发布）将在后续迭代中完善。
"""

from .experiment import Experiment
from .trainer import TrainingJob
from .evaluator import Evaluator
from .model_registry import ModelRegistry, RegisteredModel, ModelStatus, ModelVersion
from .ab_testing import ABTest, ResultMetrics
from .deployment import ModelDeployment, DeploymentMode

__all__ = [
    "Experiment",
    "TrainingJob",
    "Evaluator",
    "ModelRegistry",
    "RegisteredModel",
    "ModelStatus",
    "ModelVersion",
    "ABTest",
    "ResultMetrics",
    "ModelDeployment",
    "DeploymentMode",
]
