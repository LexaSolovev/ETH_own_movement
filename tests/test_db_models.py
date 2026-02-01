import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.models import Base, PriceBar, RegressionResult, Alert


@pytest.fixture
def engine():
    """Фикстура для создания тестовой БД в памяти."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Фикстура для создания сессии."""
    with Session(engine) as session:
        yield session


def test_price_bar_model(session):
    """Тест модели PriceBar."""
    timestamp = datetime.now()
    price_bar = PriceBar(
        symbol="ethusdt",
        timestamp=timestamp,
        open=2500.0,
        high=2510.0,
        low=2490.0,
        close=2505.0,
        volume=1000.0,
    )

    session.add(price_bar)
    session.commit()

    assert price_bar.id is not None
    assert price_bar.symbol == "ethusdt"
    assert price_bar.timestamp == timestamp
    assert price_bar.open == 2500.0
    assert price_bar.created_at is not None


def test_regression_result_model(session):
    """Тест модели RegressionResult."""
    timestamp = datetime.now()
    result = RegressionResult(
        timestamp=timestamp,
        alpha=0.001,
        beta=1.5,
        epsilon=0.0005,
        own_price_index=100.5,
    )

    session.add(result)
    session.commit()

    assert result.id is not None
    assert result.beta == 1.5
    assert result.epsilon == 0.0005
    assert result.created_at is not None


def test_alert_model(session):
    """Тест модели Alert."""
    timestamp = datetime.now()
    alert = Alert(
        timestamp=timestamp, message="Price changed by 1.5%", change_percent=1.5
    )

    session.add(alert)
    session.commit()

    assert alert.id is not None
    assert "1.5%" in alert.message
    assert alert.change_percent == 1.5
    assert alert.created_at is not None


def test_models_relationships(session):
    """Тест что модели не зависят друг от друга."""
    # Просто проверяем, что можем создать все три модели независимо
    timestamp = datetime.now()

    price_bar = PriceBar(
        symbol="btcusdt",
        timestamp=timestamp,
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=500.0,
    )

    regression = RegressionResult(
        timestamp=timestamp,
        alpha=0.002,
        beta=0.8,
        epsilon=-0.0003,
        own_price_index=99.8,
    )

    alert = Alert(timestamp=timestamp, message="Test alert", change_percent=None)

    session.add_all([price_bar, regression, alert])
    session.commit()

    assert price_bar.id is not None
    assert regression.id is not None
    assert alert.id is not None
