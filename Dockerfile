FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir .

ENTRYPOINT ["scopedact"]
CMD ["tour", "--database", "/data/tour.db", "--output", "/data/tour.jsonl"]
