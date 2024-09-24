FROM python:3.9.8-slim

# Set the working directory in the container
WORKDIR /root

# Update apt and install necessary packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY recommend.py .

RUN pip install --no-cache-dir --upgrade pip

# Install Python packages
RUN pip install --no-cache-dir Flask boto3
