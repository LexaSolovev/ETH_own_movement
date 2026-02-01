import math
from collections import deque
import logging
from typing import Optional, Deque
from datetime import datetime, timedelta

from config.settings import settings

logger = logging.getLogger(__name__)


class OwnPriceTracker:
    """Трекер собственной цены ETH."""

    def __init__(self, initial_index: float = 100.0):
        """
        Инициализация трекера собственной цены.

        Args:
            initial_index: Начальное значение индекса
        """
        self.initial_index = initial_index
        self.current_index = initial_index

        # История индекса за последние N минут
        self.history_window = settings.WINDOW_SIZE
        self.index_history: Deque[tuple] = deque(maxlen=self.history_window)

        # Время последнего обновления
        self.last_update_time: Optional[datetime] = None

        logger.info(f"Initialized OwnPriceTracker with initial index: {initial_index}")

    def update(self, timestamp: datetime, epsilon: float) -> float:
        """
        Обновить индекс собственной цены.

        Args:
            timestamp: Временная метка
            epsilon: Собственная доходность (остаток регрессии)

        Returns:
            Новое значение индекса
        """
        # Обновляем индекс: I_t = I_{t-1} * exp(epsilon)
        self.current_index *= math.exp(epsilon)

        # Сохраняем в историю
        self.index_history.append((timestamp, self.current_index))
        self.last_update_time = timestamp

        logger.debug(
            f"Own price index updated: {self.current_index:.4f} at {timestamp}"
        )
        return self.current_index

    def get_index_change(self, minutes: int = 60) -> Optional[float]:
        """
        Получить изменение индекса за указанное количество минут.

        Args:
            minutes: Количество минут для анализа

        Returns:
            Изменение в процентах или None, если недостаточно данных
        """
        if not self.index_history:
            return None

        current_timestamp, current_index = self.index_history[-1]
        target_time = current_timestamp - timedelta(minutes=minutes)

        # Ищем индекс в указанное время
        for timestamp, index in reversed(self.index_history):
            if timestamp <= target_time:
                change_percent = ((current_index - index) / index) * 100
                return change_percent

        # Если не нашли достаточно старых данных, используем самый старый
        if len(self.index_history) > 1:
            oldest_timestamp, oldest_index = self.index_history[0]
            if oldest_timestamp < current_timestamp:
                change_percent = ((current_index - oldest_index) / oldest_index) * 100
                return change_percent

        return None

    def should_alert(self, change_threshold: float = None) -> bool:
        """
        Проверить, нужно ли отправлять оповещение.

        Args:
            change_threshold: Порог изменения в процентах

        Returns:
            True если изменение превышает порог
        """
        if change_threshold is None:
            change_threshold = settings.ALERT_THRESHOLD * 100  # Преобразуем в проценты

        change = self.get_index_change(minutes=60)
        if change is None:
            return False

        return abs(change) >= change_threshold

    def get_current_index(self) -> float:
        """Получить текущее значение индекса."""
        return self.current_index

    def get_history_size(self) -> int:
        """Получить количество записей в истории."""
        return len(self.index_history)

    def reset(self, new_index: float = None):
        """Сбросить индекс."""
        if new_index is None:
            new_index = self.initial_index

        self.current_index = new_index
        self.index_history.clear()
        self.last_update_time = None
        logger.info(f"Own price tracker reset to index: {new_index}")
