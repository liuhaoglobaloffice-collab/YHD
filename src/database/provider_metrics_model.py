from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float
from .base import Base

class ProviderMetricSample(Base):
    __tablename__ = 'provider_metric_samples'

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    latency_ms = Column(Integer, nullable=True)
    success_rate = Column(Float, nullable=True)
