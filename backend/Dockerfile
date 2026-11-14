FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --no-dev && useradd --create-home app && mkdir -p /model-cache && chown app /model-cache
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["uvicorn", "smartdesk.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
