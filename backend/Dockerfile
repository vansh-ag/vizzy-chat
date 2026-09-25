FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock ./

# Install runtime dependencies (no dev deps)
RUN uv sync --frozen --no-dev

# Copy application source
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
