FROM python:3.12-slim

WORKDIR /app

# gcc + libpq-dev: needed to build psycopg2-binary / argon2-cffi wheels on some platforms
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first so dependency installs are cached across rebuilds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
