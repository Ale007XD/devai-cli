import httpx
import logging
import asyncio

class BaseAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Обновленный список моделей (agents/base.py)
        self.fallback_chain = [
            "meta-llama/llama-3.3-70b-instruct:free", # Самая умная (Smartest)
            "mistralai/mistral-nemo:free",            # Самая стабильная (Stable)
            "google/gemma-2-9b-it:free",              # Резерв (Backup)
            "microsoft/phi-3-medium-128k-instruct:free" # Последний шанс
        ]

    async def _call(self, model: str, messages: list, attempt: int = 0) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/skillsllm/bot",
            "X-Title": "SkillsLLM Bot"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                logging.info(f"Trying model: {model}...")
                response = await client.post(self.url, json=payload, headers=headers)
                
                # Специальная обработка для 429 (Too Many Requests) и 5xx
                if response.status_code in [429, 500, 502, 503, 504]:
                    raise ValueError(f"Server error {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    raise ValueError(f"Empty/Invalid JSON: {data}")

            except Exception as e:
                logging.error(f"Failed {model}: {e}")
                
                # Логика Fallback: берем следующую модель из списка
                next_attempt = attempt + 1
                if next_attempt < len(self.fallback_chain):
                    next_model = self.fallback_chain[next_attempt]
                    logging.warning(f"⚠️ Switching to fallback ({next_model})...")
                    # Небольшая пауза перед повтором, чтобы не спамить
                    await asyncio.sleep(1) 
                    return await self._call(next_model, messages, next_attempt)
                
                # Если все модели перебрали и ничего не помогло
                return "❌ Извините, все AI-сервисы сейчас перегружены. Попробуйте через минуту."

class Planner(BaseAgent):
    async def process(self, task: str, history: list) -> str:
        # Фильтруем историю от мусора
        valid_history = [m for m in history if isinstance(m, dict) and m.get('content')]
        
        # Системный промпт для лучшего качества
        system_msg = {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко, по делу и структурировано."}
        
        messages = [system_msg] + valid_history + [{"role": "user", "content": task}]
        
        # Начинаем с первой модели в цепочке (Llama 3.1)
        return await self._call(self.fallback_chain[0], messages)

class Verifier(BaseAgent):
    async def process(self, text: str) -> str:
        messages = [
            {"role": "system", "content": "Ты редактор. Найди ошибки и предложи улучшения. Если ошибок нет, напиши 'Ошибок нет'."},
            {"role": "user", "content": f"Текст для проверки:\n{text}"}
        ]
        return await self._call(self.fallback_chain[0], messages)
