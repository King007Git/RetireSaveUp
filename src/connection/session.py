import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings

# Initialize a new SQLAlchemy engine using create_async_engine
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create an asynchronous Context manager for handling database sessions
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session