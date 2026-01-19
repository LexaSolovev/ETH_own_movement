import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
import signal
import sys

from src.stream.binance_ws import BinanceWebSocket
from src.models.regression import RollingRegression
from src.models.own_price_tracker import OwnPriceTracker
from src.alert.alert_manager import AlertManager, AlertType
from src.db.crud import crud
from src.db.database import database
from config.settings import settings

# Создаем директорию для логов если ее нет
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)


class ETHOwnMovementApp:
    """Главное приложение для отслеживания собственных движений ETH."""

    def __init__(self):
        """Инициализация приложения."""
        # Последние цены для расчета доходностей
        self.last_prices: Dict[str, Optional[float]] = {
            settings.ETH_SYMBOL: None,
            settings.BTC_SYMBOL: None,
        }

        # Последние временные метки
        self.last_timestamps: Dict[str, Optional[datetime]] = {
            settings.ETH_SYMBOL: None,
            settings.BTC_SYMBOL: None,
        }

        # Инициализация компонентов
        self.regression = RollingRegression()
        self.price_tracker = OwnPriceTracker()
        self.alert_manager = AlertManager()

        # WebSocket клиент
        self.ws_client = BinanceWebSocket(
            on_klines_callback=self.on_klines,
            symbols=[settings.ETH_SYMBOL, settings.BTC_SYMBOL],
            interval=settings.INTERVAL,
        )

        # Флаг для остановки приложения
        self.is_running = False

        # Обработчики сигналов
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("ETH Own Movement App initialized")

    def signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.is_running = False

    async def initialize(self):
        """Инициализация приложения."""
        try:
            # Подключаемся к базе данных
            await database.connect()
            logger.info("Database connected")

            # Запускаем периодическую очистку старых данных
            asyncio.create_task(self.periodic_cleanup())

        except Exception as e:
            logger.error(f"Failed to initialize app: {e}")
            raise

    async def cleanup(self):
        """Очистка ресурсов при завершении."""
        logger.info("Cleaning up resources...")

        # Отключаем WebSocket
        if self.ws_client:
            await self.ws_client.disconnect()

        # Отключаем базу данных
        await database.disconnect()

        logger.info("Cleanup completed")

    async def periodic_cleanup(self):
        """Периодическая очистка старых данных из БД."""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Каждый час

                async with database.get_session() as session:
                    await crud.cleanup_old_data(session, days_to_keep=7)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    def calculate_return(
        self, current_price: float, last_price: float
    ) -> Optional[float]:
        """
        Рассчитать логарифмическую доходность.

        Args:
            current_price: Текущая цена
            last_price: Предыдущая цена

        Returns:
            Логарифмическая доходность или None при ошибке
        """
        if last_price is None or last_price <= 0:
            return None

        try:
            # Логарифмическая доходность: ln(P_t / P_{t-1})
            return (
                current_price / last_price
            ) - 1  # Для малых значений ≈ ln(P_t/P_{t-1})
        except Exception as e:
            logger.error(f"Error calculating return: {e}")
            return None

    def on_klines(self, kline_data: dict):
        """
        Обработчик новых kline данных.

        Args:
            kline_data: Данные свечи
        """
        try:
            # Обрабатываем в отдельной задаче, чтобы не блокировать WebSocket
            asyncio.create_task(self._process_kline(kline_data))

        except Exception as e:
            logger.error(f"Error in kline handler: {e}")

    async def _process_kline(self, kline_data: dict):
        """Обработать данные свечи."""
        symbol = kline_data["symbol"]
        timestamp = kline_data["timestamp"]
        close_price = kline_data["close"]

        try:
            # Сохраняем бар в БД
            async with database.get_session() as session:
                await crud.save_price_bar(
                    session=session,
                    symbol=symbol,
                    timestamp=timestamp,
                    open_price=kline_data["open"],
                    high=kline_data["high"],
                    low=kline_data["low"],
                    close=close_price,
                    volume=kline_data["volume"],
                )

            # Рассчитываем доходность
            last_price = self.last_prices.get(symbol)
            asset_return = self.calculate_return(close_price, last_price)

            # Обновляем последнюю цену
            self.last_prices[symbol] = close_price
            self.last_timestamps[symbol] = timestamp

            # Если это ETH и у нас есть доходность BTC, обновляем регрессию
            if symbol == settings.ETH_SYMBOL:
                await self._process_eth_data(timestamp, asset_return)
            elif symbol == settings.BTC_SYMBOL and asset_return is not None:
                # Сохраняем доходность BTC для использования при следующем обновлении ETH
                self.btc_return_cache = (timestamp, asset_return)

        except Exception as e:
            logger.error(f"Error processing kline for {symbol}: {e}")
            self.alert_manager.send_error_alert(str(e), f"KlineProcessor-{symbol}")

    async def _process_eth_data(self, timestamp: datetime, eth_return: Optional[float]):
        """Обработать данные ETH."""
        if eth_return is None:
            return

        # Получаем последнюю доходность BTC
        if not hasattr(self, "btc_return_cache"):
            return

        btc_timestamp, btc_return = self.btc_return_cache

        # Проверяем, что данные примерно одного времени
        time_diff = abs((timestamp - btc_timestamp).total_seconds())
        if time_diff > 60:  # Разница больше 60 секунд
            logger.warning(
                f"Time mismatch between ETH and BTC data: {time_diff:.0f} seconds"
            )
            return

        try:
            # Обновляем регрессию
            regression_result = self.regression.update(
                timestamp, eth_return, btc_return
            )

            if regression_result and regression_result.epsilon is not None:
                # Обновляем трекер собственной цены
                current_index = self.price_tracker.update(
                    timestamp, regression_result.epsilon
                )

                # Сохраняем результат регрессии в БД
                async with database.get_session() as session:
                    await crud.save_regression_result(
                        session=session,
                        timestamp=timestamp,
                        alpha=regression_result.alpha,
                        beta=regression_result.beta,
                        epsilon=regression_result.epsilon,
                        own_price_index=current_index,
                    )

                # Проверяем оповещения
                if not self.regression.is_ready():
                    # Регрессия только что стала готовой
                    if (
                        self.regression.get_window_size()
                        == settings.MIN_WINDOW_FOR_REGRESSION
                    ):
                        self.alert_manager.send_regression_ready_alert(
                            self.regression.get_window_size()
                        )
                else:
                    # Регрессия готова, проверяем изменение цены
                    change_percent = self.price_tracker.get_index_change(minutes=60)
                    self.alert_manager.check_price_change(change_percent, current_index)

                    # Логируем текущее состояние
                    if self.regression.get_window_size() % 10 == 0:  # Каждые 10 минут
                        logger.info(
                            f"Status: Index={current_index:.4f}, "
                            f"Beta={regression_result.beta:.4f}, "
                            f"Epsilon={regression_result.epsilon:.6f}, "
                            f"Window={self.regression.get_window_size()}"
                        )

        except Exception as e:
            logger.error(f"Error processing ETH data: {e}")
            self.alert_manager.send_error_alert(str(e), "RegressionProcessor")

    async def run(self):
        """Запустить приложение."""
        self.is_running = True

        try:
            await self.initialize()
            logger.info("Starting ETH Own Movement Tracker...")

            # Запускаем WebSocket клиент
            await self.ws_client.run_with_reconnect()

        except KeyboardInterrupt:
            logger.info("Application stopped by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
            self.alert_manager.send_error_alert(str(e), "MainApplication")
        finally:
            await self.cleanup()
            logger.info("Application shutdown complete")


async def main():
    """Точка входа в приложение."""
    app = ETHOwnMovementApp()

    try:
        await app.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
