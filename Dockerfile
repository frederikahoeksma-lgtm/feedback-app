# ─────────────────────────────────────────────────────────────────
#  EKX Live Feedback App — Dockerfile
#  Build:   docker build -t ekx-feedback .
#  Run:     docker run -p 5000:5000 ekx-feedback
# ─────────────────────────────────────────────────────────────────

# Use an official slim Python image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app.py .
COPY templates/ templates/
COPY static/    static/

# The SQLite database file will live inside the container.
# To persist data across container restarts, mount a volume:
#   docker run -p 5000:5000 -v ekx_data:/app ekx-feedback


# Expose the default port
EXPOSE 5000

# Environment variable — override with -e PORT=8080 if needed
ENV PORT=5000

# Launch the app
CMD ["python", "app.py"]
