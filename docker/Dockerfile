FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY README.md ./README.md

RUN mkdir -p /app/data /app/logs

EXPOSE 5000

CMD ["python", "backend/app.py"]
