"""
供应商情报系统 (Supplier Intelligence System)

Module 48: Supplier Intelligence
提供供应商搜索、分析、风险评估和智能推荐功能。
"""

from .models import (
    Supplier,
    SupplierContact,
    SupplierCertificate,
    SupplierRiskAssessment,
)

__all__ = [
    "Supplier",
    "SupplierContact",
    "SupplierCertificate",
    "SupplierRiskAssessment",
]
