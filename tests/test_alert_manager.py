import pytest
from datetime import datetime, timedelta
from src.alert.alert_manager import AlertManager, AlertType


def test_alert_manager_initialization():
    """Тест инициализации менеджера оповещений."""
    alerts = []

    def test_callback(message):
        alerts.append(message)

    manager = AlertManager(alert_callback=test_callback, cooldown_minutes=1)
    assert manager.cooldown_minutes == 1
    assert manager.alert_callback == test_callback


def test_price_change_alert():
    """Тест оповещения об изменении цены."""
    alerts = []

    def test_callback(message):
        alerts.append(message)

    manager = AlertManager(alert_callback=test_callback, cooldown_minutes=0)

    # Отправляем оповещение
    manager.send_price_change_alert(
        change_percent=1.5, current_index=101.5, is_positive=True
    )

    assert len(alerts) == 1
    assert "1.50%" in alerts[0]
    assert "росте" in alerts[0]


def test_cooldown():
    """Тест задержки между оповещениями."""
    alerts = []

    def test_callback(message):
        alerts.append(message)

    manager = AlertManager(alert_callback=test_callback, cooldown_minutes=10)

    # Первое оповещение должно пройти
    manager.send_price_change_alert(1.5, 101.5, True)
    assert len(alerts) == 1

    # Второе оповещение сразу же - не должно пройти из-за cooldown
    manager.send_price_change_alert(2.0, 102.0, True)
    assert len(alerts) == 1  # Количество не изменилось


def test_check_price_change():
    """Тест проверки изменения цены."""
    alerts = []

    def test_callback(message):
        alerts.append(message)

    manager = AlertManager(alert_callback=test_callback, cooldown_minutes=0)

    # Изменение ниже порога - не должно быть оповещения
    manager.check_price_change(change_percent=0.5, current_index=100.5)
    assert len(alerts) == 0

    # Изменение выше порога - должно быть оповещение
    manager.check_price_change(change_percent=1.5, current_index=101.5)
    assert len(alerts) == 1


def test_reset_cooldown():
    """Тест сброса задержки."""
    alerts = []

    def test_callback(message):
        alerts.append(message)

    manager = AlertManager(alert_callback=test_callback, cooldown_minutes=10)

    # Первое оповещение
    manager.send_price_change_alert(1.5, 101.5, True)
    assert len(alerts) == 1

    # Сбрасываем cooldown
    manager.reset_cooldown(AlertType.PRICE_CHANGE)

    # Теперь второе оповещение должно пройти
    manager.send_price_change_alert(2.0, 102.0, True)
    assert len(alerts) == 2
