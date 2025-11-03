FROM python:3.11-slim as builder

# Set working directory
WORKDIR /backend

# Install dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements.txt
COPY ../requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /backend

# Copy virtual environment from the build stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/backend/src:$PYTHONPATH"

# Copy the application code
COPY . .

# Make sure the credentials file has the right permissions
RUN if [ -f "/backend/regal-autonomy-454806-d1-edf68610c57a.json" ]; then chmod 600 /backend/regal-autonomy-454806-d1-edf68610c57a.json; fi
EXPOSE 8050

# Run Alembic migrations, then start the uvicorn application server
CMD alembic upgrade head && uvicorn mamaope_legal.main:app --host 0.0.0.0 --port 8060
