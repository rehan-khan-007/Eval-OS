# Use official Python slim image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (Render uses $PORT env var)
EXPOSE $PORT

# Run the FastAPI server using Render's dynamic PORT
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
