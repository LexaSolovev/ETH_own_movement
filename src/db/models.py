from sqlalchemy import Column, Integer, Float, String, DateTime, BigInteger
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class PriceBar(Base):
    """Модель для хранения ценовых баров."""

    __tablename__ = "price_bars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class RegressionResult(Base):
    """Модель для хранения результатов регрессии."""

    __tablename__ = "regression_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    alpha = Column(Float)
    beta = Column(Float)
    epsilon = Column(Float)  # собственная доходность
    own_price_index = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class Alert(Base):
    """Модель для хранения оповещений."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    message = Column(String(500), nullable=False)
    change_percent = Column(Float)
    created_at = Column(DateTime, server_default=func.now())