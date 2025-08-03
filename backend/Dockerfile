FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get upgrade -y && \
    pip install --upgrade pip && pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]

docker buildx build --platform=linux/amd64 -t jurassicon/foodgram_gateway .