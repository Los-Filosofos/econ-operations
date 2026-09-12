FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca

WORKDIR /service
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN useradd --create-home --uid 10001 econ && chown -R econ:econ /service
USER econ
EXPOSE 8000
CMD ["/bin/sh", "-c", "exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
