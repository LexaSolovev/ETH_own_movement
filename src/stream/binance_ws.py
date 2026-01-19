import json
import logging
import asyncio
from typing import Dict, Callable, Optional
import websockets
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """WebSocket клиент для получения данных с Binance."""

    def __init__(
            self,
            on_klines_callback: Callable[[Dict], None],
            symbols: Optional[list] = None,
            interval: str = "1m"
    ):
        """
        Инициализация WebSocket клиента.

        Args:
            on_klines_callback: Функция обратного вызова при получении новых данных
            symbols: Список символов для отслеживания
            interval: Интервал свечей
        """
        self.ws_url = settings.BINANCE_WS_URL
        self.symbols = symbols or [settings.ETH_SYMBOL, settings.BTC_SYMBOL]
        self.interval = interval
        self.on_klines_callback = on_klines_callback
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # секунд

    def _build_stream_names(self) -> list:
        """Построить имена потоков для подписки."""
        streams = []
        for symbol in self.symbols:
            stream_name = f"{symbol}@kline_{self.interval}"
            streams.append(stream_name)
        return streams

    def _build_subscription_message(self) -> dict:
        """Построить сообщение для подписки на потоки."""
        streams = self._build_stream_names()
        return {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }

    async def connect(self):
        """Подключиться к WebSocket и подписаться на потоки."""
        try:
            logger.info(f"Connecting to WebSocket: {self.ws_url}")
            self.websocket = await websockets.connect(self.ws_url, ping_interval=30)
            self.is_connected = True
            self.reconnect_attempts = 0

            # Отправляем сообщение подписки
            subscription_msg = self._build_subscription_message()
            await self.websocket.send(json.dumps(subscription_msg))
            logger.info(f"Subscribed to streams: {subscription_msg['params']}")

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """Отключиться от WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from WebSocket")

    async def listen(self):
        """Слушать входящие сообщения."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError("WebSocket is not connected")

        try:
            async for message in self.websocket:
                await self._handle_message(message)

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self.is_connected = False
            raise

    async def _handle_message(self, message: str):
        """Обработать входящее сообщение."""
        try:
            data = json.loads(message)

            # Проверяем, является ли сообщение kline
            if 'k' in data and data['k']['x']:  # x=True означает, что свеча закрыта
                kline_data = self._parse_kline_data(data)
                self.on_klines_callback(kline_data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _parse_kline_data(self, data: dict) -> dict:
        """Распарсить данные kline."""
        kline = data['k']
        return {
            'symbol': kline['s'].lower(),
            'timestamp': datetime.fromtimestamp(kline['t'] / 1000),
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v']),
            'is_closed': kline['x']
        }

    async def run_with_reconnect(self):
        """Запустить клиент с автоматическим переподключением."""
        while True:
            try:
                await self.connect()
                await self.listen()

            except (websockets.exceptions.ConnectionClosed, ConnectionError) as e:
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    delay = self.reconnect_delay * self.reconnect_attempts
                    logger.warning(f"Reconnecting in {delay} seconds... (attempt {self.reconnect_attempts})")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max reconnection attempts reached")
                    break

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break

            finally:
                await self.disconnect()