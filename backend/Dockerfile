FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app

EXPOSE 5000

CMD ["sh", "-c", "flask db upgrade && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 wsgi:app"]
