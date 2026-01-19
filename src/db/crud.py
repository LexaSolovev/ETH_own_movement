import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Tuple

from .models import PriceBar, RegressionResult, Alert
from .database import database

logger = logging.getLogger(__name__)


class CRUDOperations:
    """CRUD операции для работы с базой данных."""

    @staticmethod
    async def save_price_bar(
            session: AsyncSession,
            symbol: str,
            timestamp: datetime,
            open_price: float,
            high: float,
            low: float,
            close: float,
            volume: float
    ) -> Optional[PriceBar]:
        """Сохранить ценовой бар."""
        try:
            price_bar = PriceBar(
                symbol=symbol,
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume
            )
            session.add(price_bar)
            await session.flush()
            return price_bar
        except SQLAlchemyError as e:
            logger.error(f"Error saving price bar: {e}")
            return None

    @staticmethod
    async def save_regression_result(
            session: AsyncSession,
            timestamp: datetime,
            alpha: Optional[float],
            beta: Optional[float],
            epsilon: Optional[float],
            own_price_index: Optional[float]
    ) -> Optional[RegressionResult]:
        """Сохранить результат регрессии."""
        try:
            result = RegressionResult(
                timestamp=timestamp,
                alpha=alpha,
                beta=beta,
                epsilon=epsilon,
                own_price_index=own_price_index
            )
            session.add(result)
            await session.flush()
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error saving regression result: {e}")
            return None

    @staticmethod
    async def save_alert(
            session: AsyncSession,
            timestamp: datetime,
            message: str,
            change_percent: Optional[float] = None
    ) -> Optional[Alert]:
        """Сохранить оповещение."""
        try:
            alert = Alert(
                timestamp=timestamp,
                message=message,
                change_percent=change_percent
            )
            session.add(alert)
            await session.flush()
            return alert
        except SQLAlchemyError as e:
            logger.error(f"Error saving alert: {e}")
            return None

    @staticmethod
    async def get_recent_bars(
            session: AsyncSession,
            symbol: str,
            limit: int = 100
    ) -> List[PriceBar]:
        """Получить последние ценовые бары."""
        try:
            stmt = (
                select(PriceBar)
                .where(PriceBar.symbol == symbol)
                .order_by(PriceBar.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent bars: {e}")
            return []

    @staticmethod
    async def cleanup_old_data(
            session: AsyncSession,
            days_to_keep: int = 7
    ) -> Tuple[int, int, int]:
        """Очистить старые данные."""
        try:
            # Используем timezone-aware datetime
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            # Удаляем старые ценовые бары
            stmt_bars = delete(PriceBar).where(PriceBar.timestamp < cutoff_date)
            result_bars = await session.execute(stmt_bars)
            bars_deleted = result_bars.rowcount

            # Удаляем старые результаты регрессии
            stmt_results = delete(RegressionResult).where(RegressionResult.timestamp < cutoff_date)
            result_results = await session.execute(stmt_results)
            results_deleted = result_results.rowcount

            # Удаляем старые оповещения
            stmt_alerts = delete(Alert).where(Alert.timestamp < cutoff_date)
            result_alerts = await session.execute(stmt_alerts)
            alerts_deleted = result_alerts.rowcount

            await session.commit()

            logger.info(f"Cleaned up {bars_deleted} bars, {results_deleted} results, {alerts_deleted} alerts")
            return bars_deleted, results_deleted, alerts_deleted

        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up old data: {e}")
            await session.rollback()
            return 0, 0, 0


# Экспортируем экземпляр CRUD
crud = CRUDOperations()