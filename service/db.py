from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL, SYNC_DATABASE_URL


class Base(DeclarativeBase):
    pass


# Two engines for the same database: the FastAPI app is async (asyncpg), the Celery
# worker is sync (psycopg). Each side only ever touches its own engine.
async_engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

sync_engine = create_engine(SYNC_DATABASE_URL)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)
