# Base image with Python + Tesseract installed
FROM python:3.10-slim

# Install Tesseract OCR and required libs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run the Flask app with Gunicorn
EXPOSE 10000
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "180", "Arsip_beta_001_8Jul2025_onlineready13Jul2025:app"]

