import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """
    Конфигурация приложения, часть констант переопределяются в файле .env
    """

    # WebSocket Binance
    BINANCE_WS_URL: str = "wss://stream.binance.com:9443/ws"
    ETH_SYMBOL: str = "ethusdt"
    BTC_SYMBOL: str = "btcusdt"
    INTERVAL: str = "1m"

    # Параметры регрессии
    WINDOW_SIZE: int = 60  # 60 минут
    ALERT_THRESHOLD: float = 0.01  # 1%
    MIN_WINDOW_FOR_REGRESSION: int = 5  # минимальное количество точек для регрессии

    # База данных
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "eth_btc"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_URL: Optional[str] = None

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Оповещения
    ALERT_COOLDOWN_MINUTES: int = 5  # задержка между оповещениями

    # Заполнить
    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """Получить URL для подключения к БД."""
        if self.DB_URL:
            return self.DB_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
