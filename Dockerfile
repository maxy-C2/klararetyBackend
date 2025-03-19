# Use official Python image as base
FROM python:3.10

# Set the working directory inside the container
WORKDIR /backend

# Copy the project files into the container
COPY . /backend/

# Install dependencies
RUN apt-get update && apt-get install -y gcc python3-dev libpq-dev \
    && pip install --upgrade pip \
    && pip install python-dotenv \
    && pip install -r requirements.txt

# Expose Django default port
EXPOSE 8000

# Run Django server using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "klararety.wsgi:application"]
