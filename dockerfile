# docker build -t blk-hacking-ind-yourname-lastname .
# OS Selection: Using python:3.11-slim (Debian-based) because it provides a lightweight Linux footprint while retaining the essential C-libraries required to compile database drivers like asyncpg safely.

FROM python:3.11-slim

# Expose port 5477 in Dockerfile
EXPOSE 5477

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Application must run on port 5477 inside the container
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 5477"]