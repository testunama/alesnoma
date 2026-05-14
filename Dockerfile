FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Remove old sessions
RUN rm -f *.session *.session-journal

EXPOSE 8080

# Set working directory for session file
ENV HOME=/app

CMD ["python", "bot.py"]
