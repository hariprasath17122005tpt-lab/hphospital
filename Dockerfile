FROM python:3.11-slim

# System deps for PyMySQL + Pillow + general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libjpeg62-turbo-dev zlib1g-dev libpng-dev \
    curl default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache layer)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy project
COPY . .

# Create required dirs
RUN mkdir -p app/static/img/doctors app/static/reports

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start with retry for DB readiness
CMD ["python", "app.py"]
