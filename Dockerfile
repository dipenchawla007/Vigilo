FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY src/ src/
COPY ui/ ui/
COPY sandbox/ sandbox/

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8501

CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
