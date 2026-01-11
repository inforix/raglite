FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# Ensure uv is on PATH (installer drops binaries into ~/.local/bin)
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY app ./app
COPY core ./core
COPY infra ./infra
COPY workers ./workers
COPY alembic.ini ./
COPY alembic ./alembic

# Install dependencies
RUN uv sync --frozen

# Expose port
EXPOSE 7615

# Run migrations and start server
CMD uv run alembic upgrade head && \
    uv run uvicorn app.main:app --host 0.0.0.0 --port 7615
