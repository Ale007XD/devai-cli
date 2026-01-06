# Multi-Agent Bot Context

## Архитектура
- aiogram 3.x + SQLAlchemy async
- OpenRouter API (Qwen Planner, Gemma Verifier)
- Динамические навыки через importlib.reload()

## Правила навыков
1. Каждый навык = Router с функцией setup()
2. Команды должны начинаться с /имя_навыка
3. Логирование через Sentry

## Review Log
