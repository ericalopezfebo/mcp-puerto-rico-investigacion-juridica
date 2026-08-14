FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY server.py remote_server.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "remote_server.py"]
