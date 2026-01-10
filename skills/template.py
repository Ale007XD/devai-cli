from aiogram import Router, types
from aiogram.filters import Command

# Обязательно добавлять это для меню!
SKILL_METADATA = {
    "name": "template",
    "desc": "🛠 Тестовый навык",
    "command": "/template"
}

router = Router()

@router.message(Command("template"))
async def cmd_template(message: types.Message):
    await message.answer("Это шаблон работает!")

def setup():
    return router
