import pytest
from datetime import datetime, timedelta
from src.models.own_price_tracker import OwnPriceTracker


def test_tracker_initialization():
    """Тест инициализации трекера."""
    tracker = OwnPriceTracker(initial_index=100.0)
    assert tracker.current_index == 100.0
    assert tracker.get_history_size() == 0


def test_tracker_update():
    """Тест обновления индекса."""
    tracker = OwnPriceTracker(initial_index=100.0)
    timestamp = datetime.now()

    # Обновляем с положительным epsilon
    new_index = tracker.update(timestamp, epsilon=0.01)
    expected_index = 100.0 * (1.01)  # exp(0.01) ≈ 1 + 0.01 для малых значений
    assert abs(new_index - expected_index) < 0.1
    assert tracker.get_history_size() == 1

    # Сохраняем текущий индекс для сравнения
    previous_index = tracker.current_index

    # Обновляем с отрицательным epsilon
    new_index = tracker.update(timestamp, epsilon=-0.01)
    assert new_index < previous_index
    assert tracker.get_history_size() == 2


def test_tracker_index_change():
    """Тест расчета изменения индекса."""
    tracker = OwnPriceTracker(initial_index=100.0)
    base_time = datetime.now()

    # Добавляем исторические данные
    for i in range(5):
        timestamp = base_time - timedelta(minutes=(4 - i) * 15)  # Каждые 15 минут
        tracker.update(timestamp, epsilon=0.01)  # +1% каждый раз

    # Изменение за 60 минут должно быть примерно 4%
    change = tracker.get_index_change(minutes=60)
    assert change is not None
    assert abs(change - 4.0) < 0.5  # 4 изменения по 1%


def test_tracker_should_alert():
    """Тест проверки оповещений."""
    tracker = OwnPriceTracker(initial_index=100.0)
    base_time = datetime.now()

    # Медленные изменения - не должно быть оповещения
    for i in range(4):
        timestamp = base_time - timedelta(minutes=(3 - i) * 20)
        tracker.update(timestamp, epsilon=0.002)  # +0.2% каждый раз

    # Порог 1%, суммарное изменение 0.8% < 1%
    assert not tracker.should_alert(change_threshold=1.0)

    # Резкое изменение - должно быть оповещение
    tracker.update(base_time, epsilon=0.02)  # +2%
    # Общее изменение за 60 минут должно быть > 1%
    assert tracker.should_alert(change_threshold=1.0)


def test_tracker_reset():
    """Тест сброса трекера."""
    tracker = OwnPriceTracker(initial_index=100.0)
    timestamp = datetime.now()

    tracker.update(timestamp, epsilon=0.01)
    assert abs(tracker.current_index - 101.0) < 0.1
    assert tracker.get_history_size() == 1

    tracker.reset()
    assert tracker.current_index == 100.0
    assert tracker.get_history_size() == 0


def test_tracker_no_history():
    """Тест при отсутствии истории."""
    tracker = OwnPriceTracker(initial_index=100.0)

    # Без истории должен возвращать None
    assert tracker.get_index_change(minutes=60) is None
    assert not tracker.should_alert(change_threshold=1.0)