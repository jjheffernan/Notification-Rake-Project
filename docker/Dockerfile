FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY db ./db
RUN pip install --no-cache-dir -e ".[dev]"

FROM base AS app
ENTRYPOINT ["python", "-m", "notification_rake"]
CMD ["health"]

FROM base AS dashboard
EXPOSE 8000
CMD ["gunicorn", "notification_rake.web:app", "--bind", "0.0.0.0:8000", "--workers", "2"]

FROM base AS jupyter
COPY notebooks ./notebooks
COPY docker/jupyter-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8888
ENTRYPOINT ["/entrypoint.sh"]
