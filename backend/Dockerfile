FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /app/data

ENV DATABASE_URL=sqlite:////app/data/airquality.db

EXPOSE 8000

# Cloud Run sets PORT. Docker Compose leaves it unset and keeps port 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
