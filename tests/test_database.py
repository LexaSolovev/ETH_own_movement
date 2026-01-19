import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError

from src.db.database import Database, database


@pytest.mark.asyncio
async def test_database_connection():
    """Тест подключения к базе данных."""
    db = Database()

    with patch("src.db.database.create_async_engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.return_value.begin.return_value.__aenter__.return_value = mock_conn

        await db.connect()

        assert db.engine is not None
        assert db.async_session_factory is not None
        mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_database_disconnect():
    """Тест отключения от базы данных."""
    db = Database()
    db.engine = AsyncMock()

    await db.disconnect()

    db.engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_database_get_session():
    """Тест получения сессии."""
    db = Database()

    # Создаем правильный мок для session factory
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()

    db.async_session_factory = MagicMock(return_value=mock_session)

    async with db.get_session() as session:
        assert session == mock_session

    mock_session.commit.assert_awaited_once()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_get_session_with_error():
    """Тест получения сессии с ошибкой."""
    db = Database()

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=Exception("Test error"))
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    db.async_session_factory = MagicMock(return_value=mock_session)

    try:
        async with db.get_session() as session:
            pass
    except Exception as e:
        assert str(e) == "Test error"

    mock_session.rollback.assert_awaited_once()
    mock_session.close.assert_awaited_once()


def test_global_database_instance():
    """Тест глобального экземпляра базы данных."""
    assert isinstance(database, Database)
    assert database.engine is None
    assert database.async_session_factory is None
