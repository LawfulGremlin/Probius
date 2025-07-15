FROM python:3.12-slim

# Install system dependencies for scipy, pillow, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        python3-dev \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libpng-dev \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Probius source code and token injector
COPY . .

# Suppress Python syntax warnings
# ENV PYTHONWARNINGS="ignore::SyntaxWarning"
ENV PYTHONUNBUFFERED=1

# Set default command
CMD ["python", "probius.py"]
