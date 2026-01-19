import pytest
import numpy as np
from datetime import datetime
from src.models.regression import RollingRegression


def test_regression_initialization():
    """Тест инициализации регрессии."""
    regression = RollingRegression(window_size=10)
    assert regression.window_size == 10
    assert regression.min_window == 5
    assert regression.alpha is None
    assert regression.beta is None


def test_regression_update():
    """Тест обновления регрессии."""
    regression = RollingRegression(window_size=5)
    timestamp = datetime.now()

    # Добавляем данные
    for i in range(5):
        result = regression.update(timestamp, eth_return=0.01 * i, btc_return=0.005 * i)
        if i < 4:  # Первые 4 обновления недостаточно данных
            assert result is None
        else:  # 5-е обновление должно вернуть результат
            assert result is not None
            assert result.alpha is not None
            assert result.beta is not None
            assert result.epsilon is not None


def test_regression_coefficients():
    """Тест вычисления коэффициентов регрессии."""
    regression = RollingRegression(window_size=10)
    timestamp = datetime.now()

    # Создаем идеальную линейную зависимость: eth = 0.5 + 1.5 * btc
    for i in range(10):
        btc_return = 0.01 * i
        eth_return = 0.5 + 1.5 * btc_return + np.random.normal(0, 0.001)
        regression.update(timestamp, eth_return, btc_return)

    alpha, beta = regression.get_current_coefficients()
    assert alpha is not None
    assert beta is not None
    assert abs(alpha - 0.5) < 0.1  # С учетом шума
    assert abs(beta - 1.5) < 0.1


def test_regression_epsilon():
    """Тест вычисления остатков."""
    regression = RollingRegression(window_size=5)
    timestamp = datetime.now()

    # Добавляем данные
    for i in range(5):
        regression.update(timestamp, eth_return=0.01, btc_return=0.01)

    epsilon = regression.get_last_epsilon()
    assert epsilon is not None
    assert abs(epsilon) < 0.1  # Остаток должен быть небольшим


def test_regression_window_size():
    """Тест размера окна."""
    regression = RollingRegression(window_size=3)
    timestamp = datetime.now()

    assert regression.get_window_size() == 0

    regression.update(timestamp, 0.01, 0.01)
    assert regression.get_window_size() == 1

    regression.update(timestamp, 0.02, 0.02)
    regression.update(timestamp, 0.03, 0.03)
    assert regression.get_window_size() == 3  # Окно заполнено

    regression.update(timestamp, 0.04, 0.04)
    assert regression.get_window_size() == 3  # Окно не должно увеличиваться