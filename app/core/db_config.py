# app/core/models/engine/config.py
from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

load_dotenv()


DATABASE_URL = getenv("DATABASE_URL", "")


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_timeout=30,
    connect_args={
        "timeout": 30,
        "statement_cache_size": 0,
    },
    execution_options={"compiled_cache": None},
    pool_pre_ping=True,
)

sync_engine = create_engine(
    DATABASE_URL.replace("asyncpg", "psycopg2"),
    echo=False,
    future=True,
    execution_options={"compiled_cache": None},
    pool_pre_ping=True,
    pool_recycle=1800,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Session = sessionmaker(bind=sync_engine, autocommit=False, autoflush=True)
3