FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AUDIT_SECRET_KEY=docker-default-audit-key-change-me

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies directly (no pyproject.toml present)
RUN pip install --no-cache-dir fastapi uvicorn pydantic pytest

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use the FastAPI API server as the default entrypoint
CMD ["uvicorn", "agents.api:app", "--host", "0.0.0.0", "--port", "8000"]
