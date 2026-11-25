FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY templates/ templates/
COPY static/ static/

# Seasons to download. Override with: docker build --build-arg PGA_YEARS=2019-2025 .
ARG PGA_YEARS=2022-2025
ENV PGA_YEARS=${PGA_YEARS} \
    PORT=8000

# Run the pipeline at build time so the image ships with its dataset:
# download raw CSVs -> normalize per stat -> merge into master datasets.
RUN python -m src.download_stats \
 && python -m src.parse_stats \
 && python -m src.build_master

# Fail the build if the data or the app does not pass its tests.
COPY pytest.ini .
COPY tests/ tests/
RUN python -m pytest -q

EXPOSE ${PORT}

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 src.app:app"]
