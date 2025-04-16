FROM python:3.12.6-alpine3.19

ENV PYTHONUNBUFFERED=1
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Install system dependencies
RUN apk add --update --no-cache \
    postgresql-client \
    build-base \
    postgresql-dev \
    musl-dev \
    linux-headers \
    libffi-dev \
    libxslt-dev \
    libxml2-dev \
    rabbitmq-c-dev \
    bash \
    && rm -rf /var/cache/apk/*

# Create non-root user and required directories
RUN adduser --disabled-password --no-create-home quicksign && \
    mkdir -p /app /vol /var/log/celery /scripts && \
    chown -R quicksign:quicksign /app /vol /var/log/celery /scripts && \
    chmod -R 755 /vol
COPY --chown=quicksign:quicksign scripts/ /scripts/
# Create and activate virtual environment
COPY --chown=quicksign:quicksign requirements/ requirements/
RUN python -m venv /py && \
    chmod +x /scripts/run.sh && \
    /py/bin/pip install --upgrade pip setuptools wheel && \
    /py/bin/pip install --use-deprecated=legacy-resolver -r requirements/development.txt

# Copy application files
WORKDIR /app
COPY --chown=quicksign:quicksign . /app/

# Create and configure the run script


# Set environment variables
ENV PATH="/scripts:/py/bin:$PATH"

# Switch to non-root user
USER quicksign

# Entrypoint
CMD ["run.sh"]