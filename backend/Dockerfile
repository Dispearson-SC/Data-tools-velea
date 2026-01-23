# Use the official Playwright image which includes Python and browsers
# This ensures all system dependencies for Chromium are present
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (just to be sure, though the base image has them, 
# sometimes the python binding needs to link them or download specific versions)
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
