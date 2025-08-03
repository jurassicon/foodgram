FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get upgrade -y && \
    pip install --upgrade pip && pip install -r requirements.txt
COPY backend/ .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]