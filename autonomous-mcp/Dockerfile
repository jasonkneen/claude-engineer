FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN uv pip install --system -r requirements.txt

# Copy project files
COPY . .

# Expose port for REST API
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MCP_SELF_LEARNING=1 \
    MCP_AUTO_INSTALL=1 \
    MCP_TOOL_CREATION=1

# Start command
CMD ["python", "-m", "mcp.server", "--auto-bootstrap"]
