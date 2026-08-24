"""
演示数据生成脚本
Week 2 Day 5 - Demo Data Generation

生成供应商演示数据，包括：
- 50+ 供应商样本
- 覆盖所有业务类型
- 覆盖所有风险等级
- 联系人和证书数据
- 风险评估历史
"""

# Load environment variables before importing config
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import asyncio
import random
from datetime import datetime, timedelta
from typing import List

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.business.supplier.models import (
    Supplier,
    SupplierContact,
    SupplierCertificate,
    SupplierRiskAssessment,
    SupplierStatus,
    BusinessType,
    RiskLevel,
    CertificateType,
)
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.core.config import get_settings

logger = structlog.get_logger(__name__)

# 配置
settings = get_settings()

# ==================== 演示数据模板 ====================

# 中国供应商名称
CHINESE_SUPPLIERS = [
    "深圳华为技术有限公司",
    "广东美的集团有限公司",
    "浙江阿里巴巴网络科技有限公司",
    "杭州海康威视数字技术股份有限公司",
    "比亚迪股份有限公司",
    "小米科技有限责任公司",
    "TCL电子控股有限公司",
    "江苏恒瑞医药股份有限公司",
    "宁德时代新能源科技股份有限公司",
    "立讯精密工业股份有限公司",
]

# 国际供应商名称
INTERNATIONAL_SUPPLIERS = [
    "Samsung Electronics Ltd.",
    "LG Electronics Inc.",
    "Sony Corporation",
    "Panasonic Corporation",
    "Siemens AG",
    "Bosch GmbH",
    "Philips Electronics",
    "Schneider Electric SE",
    "ABB Ltd.",
    "Honeywell International Inc.",
]

# 中小型供应商名称模板
SUPPLIER_NAME_TEMPLATES = [
    "{region}{product}有限公司",
    "{region}{product}科技有限公司",
    "{region}{product}实业有限公司",
    "{region}{product}制造有限公司",
    "{product}(中国)有限公司",
]

REGIONS = ["深圳", "广州", "东莞", "苏州", "上海", "杭州", "宁波", "厦门", "天津", "北京"]
PRODUCTS = ["电子", "精密", "智能", "科技", "新能源", "半导体", "光学", "机械", "化工", "塑胶"]

# 城市列表
CITIES = {
    "China": ["Shenzhen", "Shanghai", "Guangzhou", "Beijing", "Hangzhou", "Suzhou", "Dongguan", "Ningbo"],
    "Taiwan": ["Taipei", "Taichung", "Kaohsiung", "Tainan"],
    "USA": ["Los Angeles", "San Francisco", "New York", "Seattle", "Austin"],
    "Germany": ["Munich", "Berlin", "Hamburg", "Stuttgart"],
    "Japan": ["Tokyo", "Osaka", "Nagoya", "Yokohama"],
    "South Korea": ["Seoul", "Busan", "Incheon"],
}

# 产品类别
PRODUCT_CATEGORIES = [
    "电子元器件",
    "机械配件",
    "塑料制品",
    "五金工具",
    "化工原料",
    "包装材料",
    "纺织品",
    "LED照明",
    "电线电缆",
    "模具制造",
]

# 行业
INDUSTRIES = [
    "电子制造",
    "机械制造",
    "化工",
    "新能源",
    "半导体",
    "汽车配件",
    "医疗器械",
    "智能硬件",
    "通讯设备",
    "工业自动化",
]

# 联系人姓名
CHINESE_NAMES = ["李明", "王芳", "张伟", "刘强", "陈静", "杨帆", "赵磊", "周婷", "吴杰", "郑丽"]
ENGLISH_NAMES = ["John Smith", "Mary Johnson", "David Lee", "Sarah Chen", "Michael Wang", "Lisa Zhang"]

# 职位
POSITIONS = ["总经理", "销售经理", "采购经理", "质量经理", "技术总监", "市场总监", "运营经理"]

# 信用评级
CREDIT_RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "C"]

# ==================== 数据生成函数 ====================


def generate_supplier_name(index: int) -> tuple[str, str]:
    """生成供应商名称"""
    if index < 5:
        # 前5个使用知名大企业
        return CHINESE_SUPPLIERS[index], "China"
    elif index < 10:
        # 5-10 使用国际企业
        return INTERNATIONAL_SUPPLIERS[index - 5], random.choice(["USA", "Germany", "Japan", "South Korea"])
    else:
        # 其余使用模板生成
        template = random.choice(SUPPLIER_NAME_TEMPLATES)
        region = random.choice(REGIONS)
        product = random.choice(PRODUCTS)
        return template.format(region=region, product=product), "China"


def generate_supplier_code(index: int) -> str:
    """生成供应商编码"""
    return f"SUP{index:04d}"


def generate_contact_name(country: str) -> tuple[str, str]:
    """生成联系人姓名"""
    if country == "China":
        return random.choice(CHINESE_NAMES), None
    else:
        name = random.choice(ENGLISH_NAMES)
        return name, name


def generate_risk_distribution() -> RiskLevel:
    """
    生成风险等级分布（符合真实场景）
    - 极低风险: 10%
    - 低风险: 40%
    - 中风险: 30%
    - 高风险: 20%
    """
    rand = random.random()
    if rand < 0.1:
        return RiskLevel.VERY_LOW
    elif rand < 0.5:
        return RiskLevel.LOW
    elif rand < 0.8:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.HIGH


async def create_supplier(session: AsyncSession, index: int) -> Supplier:
    """创建单个供应商"""
    name, country = generate_supplier_name(index)
    code = generate_supplier_code(index + 1)

    # 根据索引决定业务类型
    business_types = list(BusinessType)
    business_type = business_types[index % len(business_types)]

    # 生成基础数据
    city = random.choice(CITIES.get(country, ["Unknown"]))
    established_date = datetime.utcnow() - timedelta(days=random.randint(365, 365 * 20))
    
    # 注册资本根据公司大小分布
    if index < 5:
        registered_capital = random.uniform(50000000, 200000000)  # 大企业
        employee_count = random.randint(1000, 10000)
        annual_revenue = random.uniform(100000000, 1000000000)
    elif index < 20:
        registered_capital = random.uniform(5000000, 50000000)  # 中型企业
        employee_count = random.randint(200, 1000)
        annual_revenue = random.uniform(10000000, 100000000)
    else:
        registered_capital = random.uniform(500000, 5000000)  # 小企业
        employee_count = random.randint(50, 200)
        annual_revenue = random.uniform(1000000, 10000000)

    # 状态分布
    if index % 20 == 0:
        status = SupplierStatus.BLACKLIST
    elif index % 15 == 0:
        status = SupplierStatus.PENDING
    elif index % 10 == 0:
        status = SupplierStatus.INACTIVE
    else:
        status = SupplierStatus.ACTIVE

    # 信用评级
    credit_rating = random.choice(CREDIT_RATINGS)

    # 创建供应商
    supplier = Supplier(
        name=name,
        legal_name=name,
        code=code,
        country=country,
        city=city,
        address=f"{city} Industrial Zone, Building {random.randint(1, 50)}",
        postal_code=f"{random.randint(100000, 999999)}",
        business_type=business_type,
        product_category=random.choice(PRODUCT_CATEGORIES),
        industry=random.choice(INDUSTRIES),
        established_date=established_date,
        registered_capital=registered_capital,
        employee_count=employee_count,
        annual_revenue=annual_revenue,
        phone=f"+86-{random.randint(10000000000, 19999999999)}",
        email=f"contact@{code.lower()}.com",
        website=f"https://www.{code.lower()}.com",
        credit_rating=credit_rating,
        has_iso9001=random.choice([True, False]),
        has_iso14001=random.choice([True, False]),
        has_export_license=country != "China" or random.choice([True, False]),
        cooperation_years=random.randint(1, 10) if status == SupplierStatus.ACTIVE else 0,
        total_orders=random.randint(10, 500) if status == SupplierStatus.ACTIVE else 0,
        total_amount=random.uniform(100000, 5000000) if status == SupplierStatus.ACTIVE else 0,
        status=status,
        is_verified=random.choice([True, False]),
        description=f"Professional {business_type.value} specializing in {random.choice(PRODUCT_CATEGORIES)}",
        source="manual",
        created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365)),
    )

    session.add(supplier)
    await session.flush()  # 获取 supplier.id

    logger.info("supplier_created", name=name, code=code, status=status.value)

    return supplier


async def create_contacts(session: AsyncSession, supplier: Supplier, count: int = 2):
    """为供应商创建联系人"""
    for i in range(count):
        name, name_en = generate_contact_name(supplier.country)
        
        contact = SupplierContact(
            supplier_id=supplier.id,
            name=name,
            name_en=name_en,
            position=random.choice(POSITIONS),
            department=random.choice(["销售部", "采购部", "技术部", "质量部"]),
            phone=f"+86-{random.randint(10000000000, 19999999999)}",
            mobile=f"+86-{random.randint(13000000000, 19999999999)}",
            email=f"{name.lower().replace(' ', '.')}@{supplier.code.lower()}.com",
            wechat=f"wx{random.randint(100000, 999999)}",
            is_primary=(i == 0),
            is_decision_maker=(i == 0 and random.choice([True, False])),
            created_at=supplier.created_at,
        )
        session.add(contact)

    logger.info("contacts_created", supplier_id=supplier.id, count=count)


async def create_certificates(session: AsyncSession, supplier: Supplier):
    """为供应商创建证书"""
    certificates_to_add = []
    
    # 营业执照（必有）
    certificates_to_add.append({
        "type": CertificateType.BUSINESS_LICENSE,
        "name": "营业执照",
        "number": f"BL{random.randint(100000000000, 999999999999)}",
    })

    # ISO 9001
    if supplier.has_iso9001:
        certificates_to_add.append({
            "type": CertificateType.ISO9001,
            "name": "ISO 9001:2015 Quality Management System",
            "number": f"ISO9001-{random.randint(10000, 99999)}",
        })

    # ISO 14001
    if supplier.has_iso14001:
        certificates_to_add.append({
            "type": CertificateType.ISO14001,
            "name": "ISO 14001:2015 Environmental Management System",
            "number": f"ISO14001-{random.randint(10000, 99999)}",
        })

    # 出口许可证
    if supplier.has_export_license:
        certificates_to_add.append({
            "type": CertificateType.EXPORT_LICENSE,
            "name": "Export License",
            "number": f"EXP{random.randint(1000000, 9999999)}",
        })

    # 随机添加其他证书
    if random.random() > 0.5:
        certificates_to_add.append({
            "type": random.choice([CertificateType.CE, CertificateType.ROHS, CertificateType.FDA]),
            "name": "CE Certification",
            "number": f"CE{random.randint(100000, 999999)}",
        })

    for cert_data in certificates_to_add:
        issue_date = datetime.utcnow() - timedelta(days=random.randint(365, 1825))
        expiry_date = issue_date + timedelta(days=random.randint(1095, 1825))
        
        # 部分证书已过期（用于测试风险评估）
        if random.random() < 0.1:
            expiry_date = datetime.utcnow() - timedelta(days=random.randint(1, 365))

        certificate = SupplierCertificate(
            supplier_id=supplier.id,
            certificate_type=cert_data["type"],
            certificate_name=cert_data["name"],
            certificate_number=cert_data["number"],
            issuing_authority="China Quality Certification Centre" if supplier.country == "China" else "International Certification Body",
            issuing_country=supplier.country,
            issue_date=issue_date,
            expiry_date=expiry_date,
            is_verified=random.choice([True, False]),
            created_at=supplier.created_at,
        )
        session.add(certificate)

    logger.info("certificates_created", supplier_id=supplier.id, count=len(certificates_to_add))


async def assess_supplier_risk(session: AsyncSession, supplier: Supplier):
    """评估供应商风险"""
    agent = SupplierRiskAgent(session)
    
    try:
        assessment = await agent.assess_risk(supplier_id=supplier.id)
        logger.info(
            "risk_assessment_completed",
            supplier_id=supplier.id,
            risk_level=assessment.risk_level.value,
            risk_score=assessment.risk_score
        )
    except Exception as e:
        logger.error("risk_assessment_failed", supplier_id=supplier.id, error=str(e))


async def generate_demo_data(total_suppliers: int = 50):
    """
    生成演示数据主函数
    
    Args:
        total_suppliers: 要生成的供应商数量
    """
    logger.info("demo_data_generation_started", total_suppliers=total_suppliers)

    # 创建数据库引擎
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )

    # 创建会话
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # 生成供应商
            for i in range(total_suppliers):
                logger.info("generating_supplier", index=i + 1, total=total_suppliers)
                
                # 创建供应商
                supplier = await create_supplier(session, i)
                
                # 创建联系人
                contact_count = random.randint(1, 3)
                await create_contacts(session, supplier, contact_count)
                
                # 创建证书
                await create_certificates(session, supplier)
                
                # 提交当前供应商及其关联数据
                await session.commit()
                
                # 风险评估（需要supplier已提交到数据库）
                await assess_supplier_risk(session, supplier)
                await session.commit()

            logger.info("demo_data_generation_completed", total_suppliers=total_suppliers)
            
            # 统计信息
            print("\n" + "=" * 80)
            print("✅ 演示数据生成完成！")
            print("=" * 80)
            print(f"✅ 总供应商数: {total_suppliers}")
            print(f"✅ 联系人数: ~{total_suppliers * 2}")
            print(f"✅ 证书数: ~{total_suppliers * 3}")
            print(f"✅ 风险评估数: {total_suppliers}")
            print("\n📊 供应商状态分布:")
            print(f"   - 活跃 (ACTIVE): ~{int(total_suppliers * 0.7)}")
            print(f"   - 待审核 (PENDING): ~{int(total_suppliers * 0.1)}")
            print(f"   - 停用 (INACTIVE): ~{int(total_suppliers * 0.15)}")
            print(f"   - 黑名单 (BLACKLIST): ~{int(total_suppliers * 0.05)}")
            print("\n⚠️ 风险等级分布:")
            print(f"   - 极低风险 (VERY_LOW): ~{int(total_suppliers * 0.1)}")
            print(f"   - 低风险 (LOW): ~{int(total_suppliers * 0.4)}")
            print(f"   - 中风险 (MEDIUM): ~{int(total_suppliers * 0.3)}")
            print(f"   - 高风险 (HIGH): ~{int(total_suppliers * 0.2)}")
            print("\n🚀 现在可以启动系统并访问 Dashboard!")
            print("=" * 80 + "\n")

        except Exception as e:
            logger.error("demo_data_generation_failed", error=str(e))
            await session.rollback()
            raise
        finally:
            await engine.dispose()


# ==================== 主入口 ====================


if __name__ == "__main__":
    import sys
    
    # 可选参数：供应商数量
    total = 50
    if len(sys.argv) > 1:
        try:
            total = int(sys.argv[1])
        except ValueError:
            print("❌ 无效的供应商数量参数，使用默认值 50")
    
    print(f"\n🚀 开始生成 {total} 个供应商演示数据...\n")
    
    asyncio.run(generate_demo_data(total_suppliers=total))
