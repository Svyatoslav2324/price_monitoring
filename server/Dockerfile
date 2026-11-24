FROM python:3.12.3-slim-bookworm AS python-deps
WORKDIR /srv
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python-deps AS backend
COPY app app
COPY create_db.py .

FROM python-deps AS ozon
COPY requirements-ozon.txt install_ozon_browser.py .
RUN pip install --no-cache-dir -r requirements-ozon.txt && python -m playwright install-deps firefox && python install_ozon_browser.py
COPY app app
