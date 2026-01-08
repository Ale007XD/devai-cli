import os
import sys
import signal
import importlib
import logging
import sentry_sdk
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import init_db, save_message, get_user_context
from agents.base import Planner, Verifier

# Загрузка переменных
load_dotenv()
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN", ""))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Инициализация бота
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
planner = Planner(os.getenv("OPENROUTER_API_KEY"))
verifier = Verifier(os.getenv("OPENROUTER_API_KEY"))

# Фильтр администратора
class AdminFilter(BaseFilter):
    async def __call__(self, m: types.Message) -> bool:
        return str(m.from_user.id) == os.getenv("ADMIN_ID")

# Middleware для сохранения истории
class HistoryMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message) and event.text and not event.text.startswith('/'):
            await save_message(event.from_user.id, "user", event.text)
        return await handler(event, data)

dp.message.outer_middleware(HistoryMiddleware())

# --- Динамическая загрузка навыков (ИСПРАВЛЕНО) ---
def load_skills():
    dp.sub_routers.clear()
    
    # Создаем папку если нет
    if not os.path.exists("skills"): 
        os.makedirs("skills")
        
    loaded_count = 0
    for f in os.listdir("skills"):
        if f.endswith(".py") and not f.startswith("__"):
            try:
                module_name = f"skills.{f[:-3]}"
                
                # Принудительная перезагрузка модуля
                if module_name in sys.modules:
                    mod = importlib.reload(sys.modules[module_name])
                else:
                    mod = importlib.import_module(module_name)
                
                if hasattr(mod, "setup"): 
                    dp.include_router(mod.setup())
                    logging.info(f"✅ Loaded skill: {module_name}")
                    loaded_count += 1
                else:
                    logging.warning(f"⚠️ Skipped {f}: setup() not found")
            except Exception as e:
                # Логируем имя файла 'f', чтобы избежать NameError
                logging.error(f"❌ Failed to load skill {f}: {e}")
    
    logging.info(f"Total skills loaded: {loaded_count}")

# --- Хендлеры ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("🤖 **Бот активен!**\n\nКоманды:\n/plan <задача> - Планировщик\n/travel - Путешествия (AI)\n/new_skill - Создать навык\n/reload - Перезагрузка", parse_mode="Markdown")

@dp.message(Command("plan"))
async def handle_plan(m: types.Message):
    task = m.text.replace("/plan", "").strip()
    if not task: return await m.answer("Укажите задачу после команды.")
    
    wait_msg = await m.answer("⏳ Думаю...")
    history = await get_user_context(m.from_user.id)
    
    try:
        plan = await planner.process(task, history)
        verified = await verifier.process(plan)
        
        await wait_msg.delete()
        await m.answer(f"📋 **План:**\n{plan}\n\n✅ **Проверка:**\n{verified}", parse_mode="Markdown")
        await save_message(m.from_user.id, "assistant", plan)
    except Exception as e:
        await m.answer(f"Ошибка AI: {e}")

@dp.message(Command("new_skill"), AdminFilter())
async def handle_new_skill(m: types.Message):
    try:
        parts = m.text.split(maxsplit=2)
        if len(parts) < 3:
            return await m.answer("⚠️ Формат: `/new_skill filename code`", parse_mode="Markdown")
        
        filename = parts[1]
        code = parts[2]
        
        # Автодобавление .py
        if not filename.endswith(".py"): filename += ".py"
        # Защита путей
        if "/" in filename or "\\" in filename: return await m.answer("❌ Недопустимое имя файла")

        with open(f"skills/{filename}", "w", encoding="utf-8") as f: 
            f.write(code)
            
        await m.answer(f"✅ Навык `{filename}` записан. Используйте /reload")
    except Exception as e:
        await m.answer(f"❌ Ошибка записи: {e}")

@dp.message(Command("reload"), AdminFilter())
async def handle_reload(m: types.Message):
    load_skills()
    await m.answer("🔄 Навыки перезагружены.")

@dp.message(Command("review"))
async def handle_review(m: types.Message):
    history = await get_user_context(m.from_user.id)
    text = "\n".join([f"{i['role']}: {i['content']}" for i in history])
    review = await verifier.process(f"Анализ диалога: {text}")
    with open("CLAUDE.md", "a", encoding="utf-8") as f:
        f.write(f"\n\n### Review {datetime.now()}\n{review}")
    await m.answer("Анализ записан в CLAUDE.md")

# --- Запуск ---
async def main():
    await init_db()
    load_skills()
    
    # Удаляем вебхук для гарантии работы polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Graceful Shutdown для Docker
    def signal_handler(sig, frame):
        logging.info("🛑 Stopping bot...")
        asyncio.create_task(dp.stop_polling())
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
