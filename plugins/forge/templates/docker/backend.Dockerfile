# Backend image: Python wheels, the FastAPI app, migrations, and the environment's shared and
# environment config. Secrets are never copied in; they are mounted at run time.
# Build: docker build --build-arg APP_ENV=<env> --target runtime -f docker/backend.Dockerfile -t app-backend:<env>-local .
# Build context is the repo root.

ARG PYTHON_IMAGE=python:3.11-slim-bookworm

# Stage 1: wheels from the hashed lock file
FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build
COPY backend/requirements.txt .
RUN pip wheel --require-hashes --timeout 120 --retries 8 --wheel-dir /wheels -r requirements.txt

# Stage 2: runtime. The app image (app.Dockerfile) builds on this one.
FROM ${PYTHON_IMAGE} AS runtime
ARG APP_ENV
RUN test -n "${APP_ENV}" || { echo "APP_ENV build arg is required" >&2; exit 1; }
ENV APP_ENV=${APP_ENV} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && rm -rf /wheels
WORKDIR /app
COPY backend/app /app/backend/app
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/migrations /app/backend/migrations
COPY config/application.properties /app/config/application.properties
COPY config/application-${APP_ENV}.properties /app/config/application-${APP_ENV}.properties
USER app
WORKDIR /app/backend

# Stage 3: test. The tests service targets this stage. It is last in the file.
FROM runtime AS test
USER root
COPY backend/requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir --timeout 120 --retries 8 --require-hashes -r /tmp/requirements-dev.txt \
    && rm /tmp/requirements-dev.txt
COPY tests /app/tests
COPY pytest.ini mypy.ini ruff.toml /app/
WORKDIR /app
USER app
CMD ["pytest", "-q"]
