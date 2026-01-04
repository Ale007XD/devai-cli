import httpx
import logging

class BaseAgent:
    def __init__(self, key: str):
        self.key = key
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def _call(self, model: str, messages: list) -> str:
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                r = await client.post(self.url, json={"model": model, "messages": messages}, headers=headers)
                r.raise_for_status()
                return r.json()['choices'][0]['message']['content']
            except Exception as e:
                logging.error(f"Error {model}: {e}")
                if model != "deepseek/deepseek-v3":
                    return await self._call("deepseek/deepseek-v3", messages)
                return "Ошибка: Сервис временно недоступен."

class Planner(BaseAgent):
    async def process(self, task: str, history: list) -> str:
        messages = history + [{"role": "user", "content": f"Разработай план задачи: {task}"}]
        return await self._call("qwen/qwen-2.5-coder-32b-instruct:free", messages)

class Verifier(BaseAgent):
    async def process(self, text: str) -> str:
        messages = [{"role": "user", "content": f"Проверь этот план на ошибки: {text}"}]
        return await self._call("google/gemma-2-9b-it:free", messages)
