import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """Класс для управления подключением к базе данных."""

    def __init__(self):
        self.engine = None
        self.async_session_factory = None

    async def connect(self):
        """Установить подключение к базе данных."""
        try:
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,
            )

            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Проверяем подключение
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info("Database connection established")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Закрыть подключение к базе данных."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Контекстный менеджер для получения сессии."""
        if not self.async_session_factory:
            await self.connect()

        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Глобальный экземпляр базы данных
database = Database()