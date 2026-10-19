# Root-level Dockerfile for Render (the backend Dockerfile lives in backend/).
# Render's auto-detected service uses ./Dockerfile, so we keep a copy here.
# This builds both the FastAPI backend and the Flutter web frontend, serving
# the frontend as static files from the backend.
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies + Flutter SDK prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    unzip \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter SDK
RUN git clone https://github.com/flutter/flutter.git -b stable --depth 1 /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
RUN flutter --version && flutter config --no-analytics

# Copy and build Flutter web app
COPY app/ /app/frontend/
WORKDIR /app/frontend
RUN flutter pub get && \
    flutter build web --release \
      --dart-define=API_BASE_URL=https://service-forece-ai.onrender.com/api/v1

# Back to backend
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy Flutter build output into the backend's static directory
RUN mkdir -p /app/static && cp -r /app/frontend/build/web/* /app/static/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
