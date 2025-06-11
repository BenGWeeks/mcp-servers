FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server
COPY synthesis-server.py .

# Create data directory
RUN mkdir -p /app/data

# Expose port (though MCP uses stdio)
EXPOSE 8000

# Default command
CMD ["python3", "synthesis-server.py"]