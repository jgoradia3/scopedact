FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml setup.py README.md LICENSE ./
COPY src ./src
COPY pilot/container_start.py ./pilot/container_start.py
RUN python -m pip install --no-cache-dir . && mkdir -p /state /run/private
ENTRYPOINT ["python", "/app/pilot/container_start.py"]
