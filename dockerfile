# Стадия сборки
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Основная стадия
FROM python:3.11-slim
WORKDIR /app

# Копируем зависимости из builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Копируем код
COPY . .
RUN mkdir -p skills history && \
    chmod -R 777 skills history && \
    echo "# Initial context" > CLAUDE.md

EXPOSE 8080
HEALTHCHECK CMD python -c "import sys; sys.exit(0)" || exit 1
CMD ["python", "bot.py"]
