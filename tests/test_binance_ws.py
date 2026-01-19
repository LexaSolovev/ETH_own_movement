import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.stream.binance_ws import BinanceWebSocket


def test_binance_ws_initialization():
    """Тест инициализации WebSocket клиента."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    assert ws.ws_url == "wss://stream.binance.com:9443/ws"
    assert ws.symbols == ["ethusdt", "btcusdt"]
    assert ws.interval == "1m"
    assert ws.on_klines_callback == callback
    assert not ws.is_connected


def test_build_stream_names():
    """Тест построения имен потоков."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    streams = ws._build_stream_names()
    assert streams == ["ethusdt@kline_1m", "btcusdt@kline_1m"]


def test_build_subscription_message():
    """Тест построения сообщения подписки."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    message = ws._build_subscription_message()
    assert message["method"] == "SUBSCRIBE"
    assert "ethusdt@kline_1m" in message["params"]
    assert "btcusdt@kline_1m" in message["params"]


def test_parse_kline_data():
    """Тест парсинга данных kline."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    kline_data = {
        'k': {
            's': 'ETHUSDT',
            't': 1640995200000,  # 2022-01-01 00:00:00
            'o': '2500.0',
            'h': '2510.0',
            'l': '2490.0',
            'c': '2505.0',
            'v': '1000.0',
            'x': True
        }
    }

    result = ws._parse_kline_data(kline_data)
    assert result['symbol'] == 'ethusdt'
    assert result['open'] == 2500.0
    assert result['close'] == 2505.0
    assert result['is_closed'] == True


@pytest.mark.asyncio
async def test_connect_and_disconnect():
    """Тест подключения и отключения."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    # Создаем реальный мок для websocket
    mock_websocket = AsyncMock()

    # Мокаем connect чтобы возвращал AsyncMock
    with patch('src.stream.binance_ws.websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_websocket
        await ws.connect()

        assert ws.is_connected
        assert ws.websocket == mock_websocket
        mock_websocket.send.assert_awaited_once()

    await ws.disconnect()
    assert not ws.is_connected
    mock_websocket.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_kline():
    """Тест обработки сообщения kline."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    kline_message = json.dumps({
        'k': {
            's': 'ETHUSDT',
            't': 1640995200000,
            'o': '2500.0',
            'h': '2510.0',
            'l': '2490.0',
            'c': '2505.0',
            'v': '1000.0',
            'x': True
        }
    })

    await ws._handle_message(kline_message)

    callback.assert_called_once()
    called_data = callback.call_args[0][0]
    assert called_data['symbol'] == 'ethusdt'
    assert called_data['close'] == 2505.0


@pytest.mark.asyncio
async def test_handle_message_invalid_json():
    """Тест обработки невалидного JSON."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    await ws._handle_message("invalid json")

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_not_kline():
    """Тест обработки сообщения не kline."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)

    other_message = json.dumps({
        'e': '24hrTicker',
        's': 'ETHUSDT',
        'c': '2505.0'
    })

    await ws._handle_message(other_message)

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_listen():
    """Тест прослушивания сообщений."""
    callback = MagicMock()
    ws = BinanceWebSocket(on_klines_callback=callback)
    ws.is_connected = True

    mock_websocket = AsyncMock()
    mock_websocket.__aiter__.return_value = [
        json.dumps({
            'k': {
                's': 'ETHUSDT',
                't': 1640995200000,
                'o': '2500.0',
                'h': '2510.0',
                'l': '2490.0',
                'c': '2505.0',
                'v': '1000.0',
                'x': True
            }
        })
    ]
    ws.websocket = mock_websocket

    # Запускаем на короткое время
    try:
        await asyncio.wait_for(ws.listen(), timeout=0.1)
    except asyncio.TimeoutError:
        pass

    callback.assert_called()