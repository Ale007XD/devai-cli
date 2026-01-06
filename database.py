from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, DateTime, select
from datetime import datetime

engine = create_async_engine("sqlite+aiosqlite:///history.db")
Session = async_sessionmaker(engine, class_=AsyncSession)

class Base(DeclarativeBase): pass

class ChatMessage(Base):
    __tablename__ = "history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    dt: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_message(user_id: int, role: str, content: str):
    async with Session() as s:
        s.add(ChatMessage(user_id=user_id, role=role, content=content))
        await s.commit()

async def get_user_context(user_id: int, limit: int = 10):
    async with Session() as s:
        res = await s.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.dt.desc())
            .limit(limit)
        )
        messages = res.scalars().all()
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]
