FROM node:16-alpine AS frontend-dev

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json /app/frontend/
# TODO: fix peer dependency conflicts in package.json
RUN npm install


FROM frontend-dev AS frontend
COPY frontend /app/frontend
COPY rendering /app/rendering
RUN npm run build




FROM node:16-alpine AS rendering-dev

WORKDIR /app/rendering
COPY rendering/package.json rendering/package-lock.json /app/rendering/
RUN npm install

FROM rendering-dev AS rendering
COPY rendering /app/rendering/
RUN npm run build




FROM python:3.10-alpine AS api-dev

# Install system dependencies required by weasyprint and chromium
RUN apk add --no-cache \
        glib-dev \
        pango \
        fontconfig \
        ttf-freefont \
        font-noto \
        terminus-font \
        chromium \
        gcc \
        g++ \
        qpdf-dev \
        postgresql-client \
    && fc-cache -f

# Install python packages
ENV PYTHONUNBUFFERED=on \
    PYTHONDONTWRITEBYTECODE=on
COPY api/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Configure chromium
ENV PYPPETEER_HOME=/app/pyppeteer/ \
    PYPPETEER_EXECUTABLE=/usr/lib/chromium/chrome
RUN mkdir -p /app/pyppeteer/ && \
    chown -R 1000:1000 /app/pyppeteer/

WORKDIR /app/api/



FROM api-dev as api

# Copy source code
COPY api/src /app/api

# Generate static frontend files
COPY --from=frontend /app/frontend/dist/ /app/api/frontend/
RUN DEBUG=on python3 manage.py collectstatic --no-input \
    && python3 -m whitenoise.compress /app/api/frontend/ /app/api/static/

# Copy generated PDF rendering file
COPY --from=rendering /app/rendering/dist /app/rendering/

# Configure application
ENV DEBUG=off \
    PDF_RENDER_SCRIPT_PATH=/app/rendering/bundle.js \
    MEDIA_ROOT=/data/ \
    SERVER_WORKERS=3 \
    SERVER_THREADS=4

RUN mkdir /data && chown 1000:1000 /data && chmod 777 /data
VOLUME [ "/data" ]


# Start server
USER 1000
EXPOSE 8000
CMD python3 manage.py migrate && \
    gunicorn --bind=:8000 --workers=${SERVER_WORKERS} --threads=${SERVER_THREADS} reportcreator_api.wsgi:application
