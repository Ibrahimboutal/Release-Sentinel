FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN python -m pip install --no-cache-dir -e "."

# Expose port for web server
EXPOSE 8000

# Default command: serve the dashboard
CMD ["python", "-m", "releasesentinel", "serve", "--host", "0.0.0.0", "--port", "8000"]
