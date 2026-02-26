FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project
COPY . .

# Make entrypoint executable and collect static
RUN chmod +x entrypoint.sh && \
    mkdir -p /app/data && \
    SECRET_KEY=build-placeholder python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "nokia_nsp.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
