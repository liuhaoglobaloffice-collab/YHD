"""
供应商导入/导出工具
Week 3 Day 1 - Supplier API Enhancement

支持Excel和CSV格式的导入导出功能。
"""

import io
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.supplier.models import Supplier, SupplierStatus, BusinessType
from src.business.supplier.validators import SupplierValidator


class SupplierImportExport:
    """供应商导入/导出工具"""
    
    # Excel/CSV列映射
    COLUMN_MAPPING = {
        "供应商名称": "name",
        "法定名称": "legal_name",
        "供应商代码": "code",
        "国家": "country",
        "城市": "city",
        "地址": "address",
        "邮编": "postal_code",
        "业务类型": "business_type",
        "产品类别": "product_category",
        "行业": "industry",
        "成立日期": "established_date",
        "注册资本": "registered_capital",
        "员工数": "employee_count",
        "年营收": "annual_revenue",
        "电话": "phone",
        "邮箱": "email",
        "网址": "website",
        "信用评级": "credit_rating",
        "ISO9001": "has_iso9001",
        "ISO14001": "has_iso14001",
        "出口许可": "has_export_license",
        "状态": "status",
        "描述": "description",
    }
    
    # 业务类型映射
    BUSINESS_TYPE_MAPPING = {
        "制造商": BusinessType.MANUFACTURER,
        "批发商": BusinessType.TRADING,
        "分销商": BusinessType.DISTRIBUTOR,
        "进出口商": BusinessType.TRADING,
        "服务商": BusinessType.SERVICE,
        "代理商": BusinessType.AGENT,
        "零售商": BusinessType.TRADING,
    }
    
    # 状态映射
    STATUS_MAPPING = {
        "活跃": SupplierStatus.ACTIVE,
        "待审核": SupplierStatus.PENDING,
        "停用": SupplierStatus.INACTIVE,
        "黑名单": SupplierStatus.BLACKLIST,
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.validator = SupplierValidator(session)
    
    def parse_import_file(
        self,
        file_content: bytes,
        file_type: str = "excel"
    ) -> List[Dict[str, Any]]:
        """
        解析导入文件
        
        Args:
            file_content: 文件内容（字节）
            file_type: 文件类型 (excel/csv)
        
        Returns:
            解析后的供应商数据列表
        """
        # 读取文件
        if file_type == "excel":
            df = pd.read_excel(io.BytesIO(file_content))
        else:  # csv
            df = pd.read_csv(io.BytesIO(file_content))
        
        # 转换列名
        df = df.rename(columns=self.COLUMN_MAPPING)
        
        # 转换为字典列表
        suppliers_data = []
        for _, row in df.iterrows():
            supplier_dict = {}
            
            for col, value in row.items():
                if pd.isna(value):
                    continue
                
                # 特殊字段处理
                if col == "business_type" and value in self.BUSINESS_TYPE_MAPPING:
                    supplier_dict[col] = self.BUSINESS_TYPE_MAPPING[value]
                elif col == "status" and value in self.STATUS_MAPPING:
                    supplier_dict[col] = self.STATUS_MAPPING[value]
                elif col in ["has_iso9001", "has_iso14001", "has_export_license"]:
                    supplier_dict[col] = bool(value)
                elif col == "established_date":
                    if isinstance(value, str):
                        supplier_dict[col] = datetime.strptime(value, "%Y-%m-%d")
                    else:
                        supplier_dict[col] = value
                else:
                    supplier_dict[col] = value
            
            suppliers_data.append(supplier_dict)
        
        return suppliers_data
    
    async def import_suppliers(
        self,
        file_content: bytes,
        file_type: str = "excel",
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        导入供应商数据
        
        Args:
            file_content: 文件内容（字节）
            file_type: 文件类型 (excel/csv)
            validate: 是否验证数据
        
        Returns:
            导入结果：{"success": int, "failed": int, "errors": List, "ids": List}
        """
        try:
            # 解析文件
            suppliers_data = self.parse_import_file(file_content, file_type)
        except Exception as e:
            return {
                "success": 0,
                "failed": 0,
                "errors": [{"error": f"文件解析失败: {str(e)}"}],
                "ids": []
            }
        
        # 使用批量创建功能
        from src.business.supplier.crud import SupplierCRUD
        crud = SupplierCRUD(self.session)
        
        result = await crud.batch_create(suppliers_data, validate=validate)
        return result
    
    async def export_suppliers(
        self,
        filters: Optional[Dict[str, Any]] = None,
        file_type: str = "excel"
    ) -> bytes:
        """
        导出供应商数据
        
        Args:
            filters: 筛选条件（同advanced_search）
            file_type: 导出文件类型 (excel/csv)
        
        Returns:
            文件内容（字节）
        """
        from src.business.supplier.crud import SupplierCRUD
        crud = SupplierCRUD(self.session)
        
        # 获取供应商数据
        if filters:
            result = await crud.advanced_search(filters, page=1, page_size=10000)
            suppliers = result["items"]
        else:
            suppliers = await crud.get_all(limit=10000)
        
        # 构建DataFrame
        data = []
        for supplier in suppliers:
            row = {
                "供应商名称": supplier.name,
                "法定名称": supplier.legal_name,
                "供应商代码": supplier.code,
                "国家": supplier.country,
                "城市": supplier.city,
                "地址": supplier.address,
                "邮编": supplier.postal_code,
                "业务类型": supplier.business_type.value if supplier.business_type else "",
                "产品类别": supplier.product_category,
                "行业": supplier.industry,
                "成立日期": supplier.established_date.strftime("%Y-%m-%d") if supplier.established_date else "",
                "注册资本": supplier.registered_capital,
                "员工数": supplier.employee_count,
                "年营收": supplier.annual_revenue,
                "电话": supplier.phone,
                "邮箱": supplier.email,
                "网址": supplier.website,
                "信用评级": supplier.credit_rating,
                "ISO9001": "是" if supplier.has_iso9001 else "否",
                "ISO14001": "是" if supplier.has_iso14001 else "否",
                "出口许可": "是" if supplier.has_export_license else "否",
                "状态": supplier.status.value if supplier.status else "",
                "描述": supplier.description,
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 导出文件
        output = io.BytesIO()
        if file_type == "excel":
            df.to_excel(output, index=False, engine='openpyxl')
        else:  # csv
            df.to_csv(output, index=False, encoding='utf-8-sig')
        
        output.seek(0)
        return output.getvalue()
