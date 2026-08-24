"""
供应商情报系统 - CRUD服务
提供供应商数据的增删改查操作
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Supplier, 
    SupplierContact, 
    SupplierCertificate,
    SupplierRiskAssessment,
    SupplierStatus,
    BusinessType,
    RiskLevel
)


class SupplierCRUD:
    """供应商CRUD操作"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ==================== Supplier 主表 CRUD ====================
    
    async def create_supplier(
        self,
        name: str,
        country: str,
        product_category: str,
        **kwargs
    ) -> Supplier:
        """
        创建新供应商
        
        Args:
            name: 供应商名称
            country: 国家
            product_category: 产品类别
            **kwargs: 其他可选字段
        
        Returns:
            创建的供应商对象
        """
        supplier = Supplier(
            name=name,
            country=country,
            product_category=product_category,
            status=kwargs.get('status', SupplierStatus.PENDING),
            **{k: v for k, v in kwargs.items() if k != 'status'}
        )
        
        self.session.add(supplier)
        await self.session.commit()
        await self.session.refresh(supplier)
        
        return supplier
    
    async def get_supplier(self, supplier_id: int) -> Optional[Supplier]:
        """根据ID获取供应商"""
        result = await self.session.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.status != SupplierStatus.INACTIVE
            )
        )
        return result.scalar_one_or_none()
    
    async def get_supplier_by_code(self, code: str) -> Optional[Supplier]:
        """根据供应商编码获取"""
        result = await self.session.execute(
            select(Supplier).where(Supplier.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Supplier]:
        """根据供应商名称获取（用于重复检查）"""
        result = await self.session.execute(
            select(Supplier).where(Supplier.name == name)
        )
        return result.scalar_one_or_none()
    
    async def list_suppliers(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[SupplierStatus] = None,
        country: Optional[str] = None,
        business_type: Optional[BusinessType] = None,
        min_risk_score: Optional[float] = None
    ) -> List[Supplier]:
        """
        查询供应商列表
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            status: 筛选状态
            country: 筛选国家
            business_type: 筛选业务类型
            min_risk_score: 最低风险评分
        
        Returns:
            供应商列表
        """
        query = select(Supplier)
        
        # 构建筛选条件
        conditions = []
        if status:
            conditions.append(Supplier.status == status)
        if country:
            conditions.append(Supplier.country == country)
        if business_type:
            conditions.append(Supplier.business_type == business_type)
        if min_risk_score is not None:
            conditions.append(Supplier.risk_score >= min_risk_score)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_suppliers(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Supplier]:
        """
        搜索供应商（模糊匹配名称、产品、行业）
        
        Args:
            keyword: 搜索关键词
            skip: 跳过记录数
            limit: 返回记录数
        
        Returns:
            匹配的供应商列表
        """
        search_pattern = f"%{keyword}%"
        
        query = select(Supplier).where(
            or_(
                Supplier.name.ilike(search_pattern),
                Supplier.product_category.ilike(search_pattern),
                Supplier.industry.ilike(search_pattern),
                Supplier.country.ilike(search_pattern)
            )
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_supplier(
        self,
        supplier_id: int,
        **updates
    ) -> Optional[Supplier]:
        """
        更新供应商信息
        
        Args:
            supplier_id: 供应商ID
            **updates: 要更新的字段
        
        Returns:
            更新后的供应商对象，如果不存在返回None
        """
        supplier = await self.get_supplier(supplier_id)
        if not supplier:
            return None
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(supplier, key):
                setattr(supplier, key, value)
        
        supplier.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(supplier)
        
        return supplier
    
    async def delete_supplier(self, supplier_id: int) -> bool:
        """
        删除供应商（软删除）
        
        Args:
            supplier_id: 供应商ID
        
        Returns:
            是否删除成功
        """
        supplier = await self.get_supplier(supplier_id)
        if not supplier:
            return False
        
        # 软删除：改为INACTIVE状态
        supplier.status = SupplierStatus.INACTIVE
        supplier.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def blacklist_supplier(
        self,
        supplier_id: int,
        reason: str
    ) -> Optional[Supplier]:
        """
        将供应商加入黑名单
        
        Args:
            supplier_id: 供应商ID
            reason: 拉黑原因
        
        Returns:
            更新后的供应商对象
        """
        supplier = await self.get_supplier(supplier_id)
        if not supplier:
            return None
        
        supplier.status = SupplierStatus.BLACKLIST
        supplier.notes = f"[BLACKLIST] {reason}\n\n{supplier.notes or ''}"
        supplier.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(supplier)
        
        return supplier
    
    # ==================== Contact 联系人 CRUD ====================
    
    async def add_contact(
        self,
        supplier_id: int,
        name: str,
        **kwargs
    ) -> Optional[SupplierContact]:
        """
        添加供应商联系人
        
        Args:
            supplier_id: 供应商ID
            name: 联系人姓名
            **kwargs: 其他字段（job_title, email, phone, etc）
        
        Returns:
            创建的联系人对象，如果供应商不存在返回None
        """
        # 验证供应商存在
        supplier = await self.get_supplier(supplier_id)
        if not supplier:
            return None
        
        contact = SupplierContact(
            supplier_id=supplier_id,
            name=name,
            **kwargs
        )
        
        self.session.add(contact)
        await self.session.commit()
        await self.session.refresh(contact)
        
        return contact
    
    async def get_contacts(self, supplier_id: int) -> List[SupplierContact]:
        """获取供应商所有联系人"""
        result = await self.session.execute(
            select(SupplierContact)
            .where(SupplierContact.supplier_id == supplier_id)
            .order_by(SupplierContact.is_primary.desc(), SupplierContact.name)
        )
        return list(result.scalars().all())
    
    async def update_contact(
        self,
        contact_id: int,
        **updates
    ) -> Optional[SupplierContact]:
        """更新联系人信息"""
        result = await self.session.execute(
            select(SupplierContact).where(SupplierContact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return None
        
        for key, value in updates.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        
        contact.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(contact)
        
        return contact
    
    async def delete_contact(self, contact_id: int) -> bool:
        """删除联系人"""
        result = await self.session.execute(
            select(SupplierContact).where(SupplierContact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return False
        
        await self.session.delete(contact)
        await self.session.commit()
        return True
    
    # ==================== Certificate 证书 CRUD ====================
    
    async def add_certificate(
        self,
        supplier_id: int,
        certificate_type: str,
        certificate_number: str,
        issue_date: datetime,
        expiry_date: datetime,
        **kwargs
    ) -> Optional[SupplierCertificate]:
        """
        添加供应商认证证书
        
        Args:
            supplier_id: 供应商ID
            certificate_type: 证书类型
            certificate_number: 证书编号
            issue_date: 颁发日期
            expiry_date: 过期日期
            **kwargs: 其他字段
        
        Returns:
            创建的证书对象
        """
        # 验证供应商存在
        supplier = await self.get_supplier(supplier_id)
        if not supplier:
            return None
        
        certificate = SupplierCertificate(
            supplier_id=supplier_id,
            certificate_type=certificate_type,
            certificate_number=certificate_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            **kwargs
        )
        
        self.session.add(certificate)
        await self.session.commit()
        await self.session.refresh(certificate)
        
        return certificate
    
    async def get_certificates(
        self,
        supplier_id: int,
        include_expired: bool = False
    ) -> List[SupplierCertificate]:
        """
        获取供应商所有证书
        
        Args:
            supplier_id: 供应商ID
            include_expired: 是否包含过期证书
        
        Returns:
            证书列表
        """
        query = select(SupplierCertificate).where(
            SupplierCertificate.supplier_id == supplier_id
        )
        
        if not include_expired:
            query = query.where(
                SupplierCertificate.expiry_date > datetime.utcnow()
            )
        
        query = query.order_by(SupplierCertificate.expiry_date.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_certificate(
        self,
        certificate_id: int,
        **updates
    ) -> Optional[SupplierCertificate]:
        """更新证书信息"""
        result = await self.session.execute(
            select(SupplierCertificate).where(SupplierCertificate.id == certificate_id)
        )
        certificate = result.scalar_one_or_none()
        
        if not certificate:
            return None
        
        for key, value in updates.items():
            if hasattr(certificate, key):
                setattr(certificate, key, value)
        
        certificate.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(certificate)
        
        return certificate
    
    # ==================== Risk Assessment 风险评估 CRUD ====================
    
    async def create_risk_assessment(
        self,
        supplier_id: int,
        compliance_score: float,
        financial_score: float,
        delivery_score: float,
        quality_score: float,
        communication_score: float,
        **kwargs
    ) -> Optional[SupplierRiskAssessment]:
        """
        创建供应商风险评估
        
        Args:
            supplier_id: 供应商ID
            compliance_score: 合规评分 (0-100)
            financial_score: 财务评分 (0-100)
            delivery_score: 交付评分 (0-100)
            quality_score: 质量评分 (0-100)
            communication_score: 沟通评分 (0-100)
            **kwargs: 其他字段
        
        Returns:
            创建的风险评估对象
        """
        # 验证供应商存在
        supplier = await self.get_supplier(supplier_id)
        if not supplier:
            return None
        
        # 计算综合评分
        overall_score = (
            compliance_score + financial_score + delivery_score + 
            quality_score + communication_score
        ) / 5
        
        # 根据评分确定风险等级
        if overall_score >= 80:
            risk_level = RiskLevel.LOW
        elif overall_score >= 60:
            risk_level = RiskLevel.MEDIUM
        elif overall_score >= 40:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        assessment = SupplierRiskAssessment(
            supplier_id=supplier_id,
            compliance_score=compliance_score,
            financial_score=financial_score,
            delivery_score=delivery_score,
            quality_score=quality_score,
            communication_score=communication_score,
            overall_score=overall_score,
            risk_level=risk_level,
            **kwargs
        )
        
        self.session.add(assessment)
        
        # 同步更新供应商表的risk_score
        supplier.risk_score = overall_score
        supplier.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(assessment)
        
        return assessment
    
    async def get_latest_risk_assessment(
        self,
        supplier_id: int
    ) -> Optional[SupplierRiskAssessment]:
        """获取供应商最新风险评估"""
        result = await self.session.execute(
            select(SupplierRiskAssessment)
            .where(SupplierRiskAssessment.supplier_id == supplier_id)
            .order_by(SupplierRiskAssessment.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_risk_assessment_history(
        self,
        supplier_id: int,
        limit: int = 10
    ) -> List[SupplierRiskAssessment]:
        """获取供应商风险评估历史"""
        result = await self.session.execute(
            select(SupplierRiskAssessment)
            .where(SupplierRiskAssessment.supplier_id == supplier_id)
            .order_by(SupplierRiskAssessment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ==================== 统计分析 ====================
    
    async def get_supplier_count(self) -> dict:
        """获取供应商统计数量"""
        result = await self.session.execute(
            select(
                Supplier.status,
                func.count(Supplier.id).label('count')
            ).group_by(Supplier.status)
        )
        
        stats = {row.status.value: row.count for row in result.all()}
        
        # 总数
        total = sum(stats.values())
        stats['total'] = total
        
        return stats
    
    async def get_suppliers_by_country(self) -> dict:
        """按国家统计供应商数量"""
        result = await self.session.execute(
            select(
                Supplier.country,
                func.count(Supplier.id).label('count')
            )
            .where(Supplier.status == SupplierStatus.ACTIVE)
            .group_by(Supplier.country)
            .order_by(func.count(Supplier.id).desc())
        )
        
        return {row.country: row.count for row in result.all()}
    
    async def get_high_risk_suppliers(self, limit: int = 10) -> List[Supplier]:
        """获取高风险供应商列表"""
        result = await self.session.execute(
            select(Supplier)
            .where(
                and_(
                    Supplier.status == SupplierStatus.ACTIVE,
                    Supplier.risk_score < 60
                )
            )
            .order_by(Supplier.risk_score)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== 批量操作 ====================

    async def batch_create(
        self,
        suppliers_data: List[Dict[str, Any]],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        批量创建供应商
        
        Args:
            suppliers_data: 供应商数据列表
            validate: 是否进行数据验证
        
        Returns:
            批量创建结果：{"success": int, "failed": int, "errors": List, "ids": List}
        """
        from src.business.supplier.validators import SupplierValidator
        
        validator = SupplierValidator(self.session) if validate else None
        
        success_count = 0
        failed_count = 0
        errors = []
        created_ids = []
        
        for idx, data in enumerate(suppliers_data):
            try:
                # 数据验证
                if validator:
                    validation = await validator.validate_supplier_data(data, is_update=False)
                    if not validation["valid"]:
                        failed_count += 1
                        errors.append({"index": idx, "errors": validation["errors"]})
                        continue
                
                # 创建供应商
                supplier = Supplier(**data)
                self.session.add(supplier)
                await self.session.flush()
                
                created_ids.append(supplier.id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"index": idx, "error": str(e)})
        
        await self.session.commit()
        
        return {
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
            "ids": created_ids
        }

    async def batch_update(
        self,
        updates: List[Dict[str, Any]],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        批量更新供应商
        
        Args:
            updates: 更新数据列表，每项必须包含id字段
            validate: 是否进行数据验证
        
        Returns:
            批量更新结果：{"success": int, "failed": int, "errors": List}
        """
        from src.business.supplier.validators import SupplierValidator
        
        validator = SupplierValidator(self.session) if validate else None
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for idx, update_data in enumerate(updates):
            try:
                if "id" not in update_data:
                    failed_count += 1
                    errors.append({"index": idx, "error": "Missing 'id' field"})
                    continue
                
                supplier_id = update_data.pop("id")
                
                # 数据验证
                if validator:
                    validation = await validator.validate_supplier_data(
                        update_data,
                        is_update=True,
                        supplier_id=supplier_id
                    )
                    if not validation["valid"]:
                        failed_count += 1
                        errors.append({"index": idx, "id": supplier_id, "errors": validation["errors"]})
                        continue
                
                # 更新供应商
                result = await self.session.execute(
                    select(Supplier).where(Supplier.id == supplier_id)
                )
                supplier = result.scalar_one_or_none()
                
                if not supplier:
                    failed_count += 1
                    errors.append({"index": idx, "id": supplier_id, "error": "Supplier not found"})
                    continue
                
                # 应用更新
                for key, value in update_data.items():
                    setattr(supplier, key, value)
                
                supplier.updated_at = datetime.utcnow()
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"index": idx, "error": str(e)})
        
        await self.session.commit()
        
        return {
            "success": success_count,
            "failed": failed_count,
            "errors": errors
        }

    async def batch_delete(self, supplier_ids: List[int]) -> Dict[str, Any]:
        """
        批量删除供应商
        
        Args:
            supplier_ids: 供应商ID列表
        
        Returns:
            批量删除结果：{"success": int, "failed": int, "errors": List}
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        for supplier_id in supplier_ids:
            try:
                result = await self.session.execute(
                    select(Supplier).where(Supplier.id == supplier_id)
                )
                supplier = result.scalar_one_or_none()
                
                if not supplier:
                    failed_count += 1
                    errors.append({"id": supplier_id, "error": "Supplier not found"})
                    continue
                
                await self.session.delete(supplier)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"id": supplier_id, "error": str(e)})
        
        await self.session.commit()
        
        return {
            "success": success_count,
            "failed": failed_count,
            "errors": errors
        }

    # ==================== 高级搜索 ====================

    async def advanced_search(
        self,
        filters: Dict[str, Any],
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        高级搜索（多条件组合）
        
        Args:
            filters: 搜索条件字典，支持字段：
                - name: 名称（模糊匹配）
                - status: 状态（精确匹配）
                - country: 国家（精确匹配）
                - business_type: 业务类型（精确匹配）
                - capital_min: 注册资本最小值
                - capital_max: 注册资本最大值
                - established_after: 成立时间后（日期）
                - established_before: 成立时间前（日期）
            sort_by: 排序字段
            sort_order: 排序方向 (asc/desc)
            page: 页码
            page_size: 每页数量
        
        Returns:
            搜索结果：{"items": List, "total": int, "page": int, "page_size": int, "stats": Dict}
        """
        query = select(Supplier)
        conditions = []
        
        # 构建查询条件
        if "name" in filters and filters["name"]:
            conditions.append(Supplier.name.like(f"%{filters['name']}%"))
        
        if "status" in filters:
            conditions.append(Supplier.status == filters["status"])
        
        if "country" in filters and filters["country"]:
            conditions.append(Supplier.country == filters["country"])
        
        if "business_type" in filters:
            conditions.append(Supplier.business_type == filters["business_type"])
        
        if "capital_min" in filters:
            conditions.append(Supplier.registered_capital >= filters["capital_min"])
        
        if "capital_max" in filters:
            conditions.append(Supplier.registered_capital <= filters["capital_max"])
        
        if "established_after" in filters:
            conditions.append(Supplier.established_date >= filters["established_after"])
        
        if "established_before" in filters:
            conditions.append(Supplier.established_date <= filters["established_before"])
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        # 排序
        if sort_by and hasattr(Supplier, sort_by):
            order_column = getattr(Supplier, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # 执行查询
        result = await self.session.execute(query)
        items = list(result.scalars().all())
        
        # 统计信息
        stats = {}
        if items:
            # 平均注册资本
            avg_capital_query = select(func.avg(Supplier.registered_capital))
            if conditions:
                avg_capital_query = avg_capital_query.where(and_(*conditions))
            avg_capital = await self.session.scalar(avg_capital_query)
            stats["avg_capital"] = float(avg_capital) if avg_capital else 0
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "stats": stats
        }
