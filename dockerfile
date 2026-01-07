# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости в локальную пользовательскую директорию
# Важно: root по умолчанию ставит в /root/.local при флаге --user
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем установленные библиотеки из builder
# В python:slim по умолчанию пользователь root, его домашняя папка /root
COPY --from=builder /root/.local /root/.local

# Обновляем PATH, чтобы Python видел установленные пакеты
ENV PATH=/root/.local/bin:$PATH

# Копируем код приложения
COPY . .

# Создаем необходимые директории
RUN mkdir -p skills history && \
    chmod -R 777 skills history && \
    touch CLAUDE.md && \
    chmod 666 CLAUDE.md

# Healthcheck
HEALTHCHECK CMD python -c "import sys; sys.exit(0)" || exit 1

# Запуск
CMD ["python", "bot.py"]
