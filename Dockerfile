# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code to the working directory
COPY . .

# Make port 8080 available to the world outside this container
# The PORT environment variable is set by Cloud Run.
# We default to 8080, but Cloud Run will override this.
ENV PORT 8080

# Run uvicorn when the container launches
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
