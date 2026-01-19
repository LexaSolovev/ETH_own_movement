import pytest
import asyncio
from datetime import datetime
from src.models.regression import RollingRegression
from src.models.own_price_tracker import OwnPriceTracker
from src.alert.alert_manager import AlertManager


@pytest.mark.asyncio
async def test_integration_flow():
    """Интеграционный тест основного потока данных."""
    # Создаем компоненты
    regression = RollingRegression(window_size=5)
    tracker = OwnPriceTracker()
    alert_manager = AlertManager(cooldown_minutes=0)

    alerts = []

    def alert_callback(message):
        alerts.append(message)

    alert_manager.alert_callback = alert_callback

    # Имитируем поток данных
    timestamp = datetime.now()

    # Симулируем данные: ETH зависит от BTC с коэффициентом 1.5
    for i in range(10):
        btc_return = 0.01 * (i + 1)
        eth_return = 0.5 + 1.5 * btc_return

        # Обновляем регрессию
        result = regression.update(timestamp, eth_return, btc_return)

        if result and result.epsilon is not None:
            # Обновляем трекер
            current_index = tracker.update(timestamp, result.epsilon)

            # Проверяем оповещения
            change_percent = tracker.get_index_change(minutes=60)
            alert_manager.check_price_change(change_percent, current_index)

    # Проверяем результаты
    assert regression.is_ready()
    assert tracker.get_history_size() > 0
    assert len(alerts) <= 1  # Может быть 0 или 1 оповещение


@pytest.mark.asyncio
async def test_error_handling():
    """Тест обработки ошибок в интеграционном потоке."""
    regression = RollingRegression(window_size=5, min_window=3)  # Уменьшаем min_window
    tracker = OwnPriceTracker()

    alerts = []

    def alert_callback(message):
        alerts.append(message)

    alert_manager = AlertManager(alert_callback=alert_callback, cooldown_minutes=0)

    timestamp = datetime.now()

    # Нормальные данные (нужно минимум 3 для регрессии с min_window=3)
    result = None
    for i in range(5):
        # Делаем разные значения для ETH и BTC, чтобы регрессия работала
        eth_return = 0.01 * i + 0.001  # Немного разные
        btc_return = 0.01 * i
        result = regression.update(timestamp, eth_return, btc_return)

    # После 5 обновлений регрессия должна быть готова
    assert result is not None
    assert regression.is_ready()

    # Обновляем трекер, если есть epsilon
    if result and result.epsilon is not None:
        tracker.update(timestamp, result.epsilon)

    # Проверяем, что трекер обновился (должно быть 1 обновление)
    assert tracker.get_history_size() == 1

    # Проверяем оповещения
    alert_manager.check_price_change(0.5, 100.5)
    assert len(alerts) == 0  # Изменение 0.5% < порога 1%


def test_min_window_regression():
    """Тест минимального окна для регрессии."""
    regression = RollingRegression(window_size=5)
    timestamp = datetime.now()

    # Первые 4 обновления - недостаточно данных
    for i in range(4):
        result = regression.update(timestamp, 0.01, 0.01)
        assert result is None
        assert not regression.is_ready()

    # 5-е обновление - достаточно данных
    result = regression.update(timestamp, 0.01, 0.01)
    assert result is not None
    assert regression.is_ready()