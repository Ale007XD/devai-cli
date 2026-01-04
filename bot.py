import os, importlib, logging, sentry_sdk
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import init_db, SessionLocal, ChatMessage, save_message, get_user_context
from agents.base import Planner, Verifier

load_dotenv()
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
planner = Planner(os.getenv("OPENROUTER_API_KEY"))
verifier = Verifier(os.getenv("OPENROUTER_API_KEY"))

class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return str(message.from_user.id) == os.getenv("ADMIN_ID")

class HistoryMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if event.text:
            await save_message(event.from_user.id, "user", event.text)
        return await handler(event, data)

dp.message.outer_middleware(HistoryMiddleware())

def load_skills():
    dp.sub_routers.clear()
    for f in os.listdir("skills"):
        if f.endswith(".py") and not f.startswith("__"):
            mod = importlib.import_module(f"skills.{f[:-3]}")
            importlib.reload(mod)
            dp.include_router(mod.setup())

@dp.message(Command("plan"))
async def handle_plan(message: types.Message):
    task = message.text.replace("/plan", "").strip()
    history = await get_user_context(message.from_user.id)
    # Передаем историю агенту для контекста пользователя
    plan = await planner.process(task, history)
    verified = await verifier.process(plan)
    await message.answer(f"**Plan:**
{plan}

**Verify:**
{verified}", parse_mode="Markdown")
    await save_message(message.from_user.id, "assistant", plan)

@dp.message(Command("reload"), AdminFilter())
async def handle_reload(message: types.Message):
    load_skills()
    await message.answer("✅ Skills reloaded.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    load_skills()
    dp.run_polling(bot)
