# Menu Planner - Docker Image
# Build with: docker build -t menu-planner .
# Run with: docker run -p 5000:5000 menu-planner

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies. gosu lets the entrypoint drop from root to
# appuser after fixing volume ownership, without the signal-handling quirks
# of `su` (gosu execs directly, so gunicorn stays PID 1's actual child and
# still receives SIGTERM correctly on Railway restarts/deploys).
RUN apt-get update && apt-get install -y \
    gcc \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Keep a pristine copy of the baked-in seed data files separate from /app/data
# itself - a Railway persistent volume mounted at /app/data will shadow
# whatever was baked into that path at image-build time, so the entrypoint
# script needs an untouched source to restore missing seed files from on
# first boot against an empty/new volume.
RUN mkdir -p /app/data-seed && cp -r data/. /app/data-seed/

# Create necessary directories
RUN mkdir -p data logs

RUN chmod +x docker-entrypoint.sh

# Set environment variables
ENV FLASK_APP=deployment/flask_app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Create non-root user for security. Deliberately NOT switching to it here
# (no USER appuser) - a Railway persistent volume mounted at /app/data at
# container *runtime* brings its own ownership (often root) which overrides
# whatever this build-time chown set, so appuser ends up unable to write to
# /app/data ("Permission denied") even though this RUN line looks like it
# should have fixed it. The entrypoint script now starts as root, fixes
# ownership of the actual mounted volume, then drops to appuser itself.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Health check (shell form so $PORT expands at container runtime)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Expose default port (informational only; Railway assigns the real one at runtime)
EXPOSE 5000

# Container starts as root (entrypoint fixes volume ownership, then drops
# to appuser via gosu before running migrations/gunicorn - see docker-entrypoint.sh)
CMD ["./docker-entrypoint.sh"]
