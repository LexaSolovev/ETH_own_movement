import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum

from config.settings import settings

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Типы оповещений."""

    PRICE_CHANGE = "price_change"
    REGRESSION_READY = "regression_ready"
    ERROR = "error"


class AlertManager:
    """Менеджер оповещений."""

    def __init__(
        self,
        alert_callback: Optional[Callable[[str], None]] = None,
        cooldown_minutes: int = None,
    ):
        """
        Инициализация менеджера оповещений.

        Args:
            alert_callback: Функция для отправки оповещений
            cooldown_minutes: Задержка между оповещениями
        """
        self.alert_callback = alert_callback or self._default_alert_callback
        self.cooldown_minutes = cooldown_minutes or settings.ALERT_COOLDOWN_MINUTES

        # Время последнего оповещения для каждого типа
        self.last_alert_times = {}

        # Порог для оповещений
        self.alert_threshold = settings.ALERT_THRESHOLD * 100  # В процентах

        logger.info(
            f"Initialized AlertManager with cooldown: {self.cooldown_minutes} minutes"
        )

    def _default_alert_callback(self, message: str):
        """Стандартный callback для оповещений (вывод в консоль)."""
        print(f"\n{'=' * 60}")
        print(f"ALERT: {message}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

    def _can_send_alert(self, alert_type: AlertType) -> bool:
        """Проверить, можно ли отправить оповещение."""
        if alert_type not in self.last_alert_times:
            return True

        last_time = self.last_alert_times[alert_type]
        cooldown_delta = timedelta(minutes=self.cooldown_minutes)

        return datetime.now() - last_time > cooldown_delta

    def _update_alert_time(self, alert_type: AlertType):
        """Обновить время последнего оповещения."""
        self.last_alert_times[alert_type] = datetime.now()

    def send_price_change_alert(
        self, change_percent: float, current_index: float, is_positive: bool
    ):
        """
        Отправить оповещение об изменении цены.

        Args:
            change_percent: Изменение в процентах
            current_index: Текущий индекс собственной цены
            is_positive: True если изменение положительное
        """
        if not self._can_send_alert(AlertType.PRICE_CHANGE):
            return

        direction = "росте" if is_positive else "падении"

        message = (
            f"Собственная цена ETH изменилась на {abs(change_percent):.2f}% "
            f"за последние 60 минут ({direction}).\n"
            f"Текущий индекс: {current_index:.4f}\n"
            f"Порог: {self.alert_threshold:.1f}%"
        )

        self.alert_callback(message)
        self._update_alert_time(AlertType.PRICE_CHANGE)

        logger.info(f"Price change alert sent: {abs(change_percent):.2f}% {direction}")

    def send_regression_ready_alert(self, window_size: int):
        """Отправить оповещение о готовности регрессии."""
        if not self._can_send_alert(AlertType.REGRESSION_READY):
            return

        message = (
            f"Регрессионная модель готова к работе.\n"
            f"Накоплено данных: {window_size} минут\n"
            f"Начинается отслеживание собственных движений ETH."
        )

        self.alert_callback(message)
        self._update_alert_time(AlertType.REGRESSION_READY)

        logger.info(f"Regression ready alert sent: {window_size} minutes of data")

    def send_error_alert(self, error_message: str, component: str = "Unknown"):
        """Отправить оповещение об ошибке."""
        if not self._can_send_alert(AlertType.ERROR):
            return

        message = f"Ошибка в компоненте {component}:\n" f"{error_message}"

        self.alert_callback(message)
        self._update_alert_time(AlertType.ERROR)

        logger.error(f"Error alert sent from {component}: {error_message}")

    def check_price_change(self, change_percent: Optional[float], current_index: float):
        """
        Проверить изменение цены и отправить оповещение при необходимости.

        Args:
            change_percent: Изменение в процентах
            current_index: Текущий индекс собственной цены
        """
        if change_percent is None:
            return

        if abs(change_percent) >= self.alert_threshold:
            is_positive = change_percent > 0
            self.send_price_change_alert(change_percent, current_index, is_positive)

    def reset_cooldown(self, alert_type: Optional[AlertType] = None):
        """
        Сбросить задержку для оповещений.

        Args:
            alert_type: Тип оповещения или None для всех
        """
        if alert_type:
            if alert_type in self.last_alert_times:
                del self.last_alert_times[alert_type]
        else:
            self.last_alert_times.clear()

        logger.info(f"Cooldown reset for {alert_type or 'all alerts'}")
