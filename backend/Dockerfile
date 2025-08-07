FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y netcat-openbsd  \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir
COPY backend/ .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
