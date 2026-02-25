FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build-time dependencies needed when wheels are unavailable.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        gfortran \
        libjpeg-dev \
        liblapack-dev \
        libopenblas-dev \
        libpng-dev \
        zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime shared libraries for scipy/pillow.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        liblapack3 \
        libopenblas0-pthread \
        libpng16-16 \
        zlib1g && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

CMD ["python", "probius.py"]