import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from src.db.crud import CRUDOperations, crud
from src.db.models import PriceBar, RegressionResult, Alert


@pytest.mark.asyncio
async def test_save_price_bar_success():
    """Тест успешного сохранения ценового бара."""
    mock_session = AsyncMock()
    # add - синхронный метод в SQLAlchemy
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    saved_bar = await CRUDOperations.save_price_bar(
        session=mock_session,
        symbol="ethusdt",
        timestamp=datetime.now(),
        open_price=2500.0,
        high=2510.0,
        low=2490.0,
        close=2505.0,
        volume=1000.0,
    )

    assert saved_bar is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_price_bar_error():
    """Тест сохранения ценового бара с ошибкой."""
    mock_session = AsyncMock()

    # Используем правильное исключение SQLAlchemy
    from sqlalchemy.exc import SQLAlchemyError

    # Мокаем add так, чтобы при вызове бросалось исключение
    mock_session.add = MagicMock(side_effect=SQLAlchemyError("DB error"))
    mock_session.flush = AsyncMock()

    saved_bar = await CRUDOperations.save_price_bar(
        session=mock_session,
        symbol="ethusdt",
        timestamp=datetime.now(),
        open_price=2500.0,
        high=2510.0,
        low=2490.0,
        close=2505.0,
        volume=1000.0,
    )

    assert saved_bar is None
    mock_session.add.assert_called_once()
    # При ошибке в add, flush не должен вызываться
    mock_session.flush.assert_not_called()


@pytest.mark.asyncio
async def test_save_regression_result_success():
    """Тест успешного сохранения результата регрессии."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    saved_result = await CRUDOperations.save_regression_result(
        session=mock_session,
        timestamp=datetime.now(),
        alpha=0.001,
        beta=1.5,
        epsilon=0.0005,
        own_price_index=100.5,
    )

    assert saved_result is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_alert_success():
    """Тест успешного сохранения оповещения."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    saved_alert = await CRUDOperations.save_alert(
        session=mock_session,
        timestamp=datetime.now(),
        message="Test alert",
        change_percent=1.5,
    )

    assert saved_alert is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_recent_bars_success():
    """Тест успешного получения последних баров."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        PriceBar(
            symbol="ethusdt",
            timestamp=datetime.now(),
            open=2500.0,
            high=2510.0,
            low=2490.0,
            close=2505.0,
            volume=1000.0,
        )
    ]
    mock_session.execute.return_value = mock_result

    bars = await CRUDOperations.get_recent_bars(
        session=mock_session, symbol="ethusdt", limit=10
    )

    assert len(bars) == 1
    assert bars[0].symbol == "ethusdt"


@pytest.mark.asyncio
async def test_get_recent_bars_error():
    """Тест получения баров с ошибкой."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("DB error")

    bars = await CRUDOperations.get_recent_bars(
        session=mock_session, symbol="ethusdt", limit=10
    )

    assert bars == []


@pytest.mark.asyncio
async def test_cleanup_old_data_success():
    """Тест успешной очистки старых данных."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_session.execute.return_value = mock_result

    bars_deleted, results_deleted, alerts_deleted = (
        await CRUDOperations.cleanup_old_data(session=mock_session, days_to_keep=7)
    )

    assert bars_deleted == 5
    assert results_deleted == 5
    assert alerts_deleted == 5
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_old_data_error():
    """Тест очистки данных с ошибкой."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("DB error")

    bars_deleted, results_deleted, alerts_deleted = (
        await CRUDOperations.cleanup_old_data(session=mock_session, days_to_keep=7)
    )

    assert bars_deleted == 0
    assert results_deleted == 0
    assert alerts_deleted == 0
    mock_session.rollback.assert_called_once()


def test_crud_instance():
    """Тест экземпляра CRUD."""
    assert isinstance(crud, CRUDOperations)
