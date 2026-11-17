FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/app/uploads

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db.py main.py init_db.py fake_jobs.py ./
COPY views ./views
COPY templates ./templates
COPY static ./static
COPY sql ./sql

RUN useradd --create-home --uid 10001 swipehire \
 && mkdir -p /app/uploads \
 && chown swipehire /app/uploads
USER swipehire

EXPOSE 8000
# Docker marks the container healthy only when the site answers AND MySQL is reachable.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=3   CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
# init_db.py waits for MySQL, creates the tables and seeds demo data once.
CMD ["sh", "-c", "python init_db.py && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --access-logfile - main:app"]
