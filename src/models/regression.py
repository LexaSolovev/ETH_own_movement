import numpy as np
from collections import deque
import logging
from typing import Optional, Tuple, Deque
from dataclasses import dataclass

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RegressionStats:
    """Статистика регрессии."""
    alpha: Optional[float]
    beta: Optional[float]
    epsilon: Optional[float]
    r_squared: Optional[float]


class RollingRegression:
    """Скользящая линейная регрессия для анализа зависимости ETH от BTC."""

    def __init__(self, window_size: int = None, min_window: int = None):
        """
        Инициализация скользящей регрессии.

        Args:
            window_size: Размер окна для регрессии
            min_window: Минимальный размер окна для вычисления регрессии
        """
        self.window_size = window_size or settings.WINDOW_SIZE
        self.min_window = min_window or settings.MIN_WINDOW_FOR_REGRESSION

        # Очереди для хранения доходностей
        self.eth_returns: Deque[float] = deque(maxlen=self.window_size)
        self.btc_returns: Deque[float] = deque(maxlen=self.window_size)

        # Временные метки
        self.timestamps: Deque = deque(maxlen=self.window_size)

        # Текущие коэффициенты
        self.alpha: Optional[float] = None
        self.beta: Optional[float] = None
        self.last_epsilon: Optional[float] = None

        logger.info(f"Initialized RollingRegression with window size: {self.window_size}")

    def update(self, timestamp, eth_return: float, btc_return: float) -> Optional[RegressionStats]:
        """
        Обновить регрессию новыми доходностями.

        Args:
            timestamp: Временная метка
            eth_return: Доходность ETH
            btc_return: Доходность BTC

        Returns:
            Статистика регрессии или None, если недостаточно данных
        """
        # Добавляем данные в очередь
        self.eth_returns.append(eth_return)
        self.btc_returns.append(btc_return)
        self.timestamps.append(timestamp)

        # Проверяем, достаточно ли данных для регрессии
        if len(self.eth_returns) < self.min_window:
            logger.debug(f"Not enough data for regression: {len(self.eth_returns)}/{self.min_window}")
            return None

        try:
            # Преобразуем в numpy массивы
            X = np.array(self.btc_returns).reshape(-1, 1)
            y = np.array(self.eth_returns)

            # Добавляем константу для intercept
            X_with_const = np.hstack([np.ones((len(X), 1)), X])

            # Вычисляем коэффициенты методом наименьших квадратов
            coeffs = np.linalg.lstsq(X_with_const, y, rcond=None)[0]

            self.alpha = float(coeffs[0])
            self.beta = float(coeffs[1])

            # Вычисляем остаток (epsilon) для последнего наблюдения
            last_eth_return = self.eth_returns[-1]
            last_btc_return = self.btc_returns[-1]
            predicted = self.alpha + self.beta * last_btc_return
            self.last_epsilon = last_eth_return - predicted

            # Вычисляем R²
            y_pred = self.alpha + self.beta * X.flatten()
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            result = RegressionStats(
                alpha=self.alpha,
                beta=self.beta,
                epsilon=self.last_epsilon,
                r_squared=float(r_squared)
            )

            logger.debug(f"Regression updated: alpha={self.alpha:.6f}, beta={self.beta:.6f}, "
                         f"epsilon={self.last_epsilon:.6f}, R²={r_squared:.4f}")

            return result

        except np.linalg.LinAlgError as e:
            logger.error(f"Linear algebra error in regression: {e}")
            return None
        except Exception as e:
            logger.error(f"Error updating regression: {e}")
            return None

    def get_current_coefficients(self) -> Tuple[Optional[float], Optional[float]]:
        """Получить текущие коэффициенты регрессии."""
        return self.alpha, self.beta

    def get_last_epsilon(self) -> Optional[float]:
        """Получить последнее значение epsilon."""
        return self.last_epsilon

    def get_window_size(self) -> int:
        """Получить текущий размер окна."""
        return len(self.eth_returns)

    def is_ready(self) -> bool:
        """Проверить, готова ли регрессия для использования."""
        return len(self.eth_returns) >= self.min_window