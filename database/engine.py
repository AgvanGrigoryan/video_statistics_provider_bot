from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import settings

engine: AsyncEngine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with automatic cleanup.
    
    Caller is responsible for explicit commit() when making modifications.
    Session automatically rolls back on exceptions.
    
    Usage for reads:
        async for session in get_async_session():
            result = await session.execute(select(Video))
            videos = result.scalars().all()
    
    Usage for writes:
        async for session in get_async_session():
            session.add(video)
            await session.commit()  # Explicit commit
    
    Yields:
        AsyncSession: Database session with transaction management

    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Closes all connections to the database

    Called when the application stops.

    Returns:
        None
    """
    await engine.dispose()