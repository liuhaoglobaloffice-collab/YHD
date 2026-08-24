"""运行风险评估 - Week 2 Day 5"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.core.config import get_settings
from src.business.supplier.risk_agent import SupplierRiskAgent

settings = get_settings()


async def run_assessments():
    """为所有供应商运行风险评估"""
    engine = create_async_engine(settings.database_url)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        agent = SupplierRiskAgent(session)
        
        print("开始风险评估...")
        for supplier_id in range(1, 16):
            try:
                result = await agent.assess_risk(supplier_id=supplier_id)
                print(f"  供应商 #{supplier_id} - 风险等级: {result['risk_level']}, 评分: {result['risk_score']}")
            except Exception as e:
                print(f"  供应商 #{supplier_id} - 失败: {e}")
        
        await session.commit()
        print("风险评估完成！")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_assessments())
