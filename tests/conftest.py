import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_websocket():
    """Фикстура для мока WebSocket."""
    mock = AsyncMock()
    mock.is_connected = True
    mock.reconnect_attempts = 0
    return mock


@pytest.fixture
def mock_database():
    """Фикстура для мока базы данных."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.get_session = AsyncMock()
    return mock


@pytest.fixture
def sample_kline_data():
    """Фикстура с примером данных kline."""
    return {
        'symbol': 'ethusdt',
        'timestamp': '2024-01-01 00:00:00',
        'open': 2500.0,
        'high': 2510.0,
        'low': 2490.0,
        'close': 2505.0,
        'volume': 1000.0,
        'is_closed': True
    }


@pytest.fixture
def event_loop():
    """Фикстура для event loop в тестах."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()