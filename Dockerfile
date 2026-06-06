# Use an officialm, lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy the dependencies file to the working directory
COPY ./requirements.txt /code/requirements.txt

# Install Python dependencies without caching to keep the image small
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application source code into the container
COPY ./app/ /code/app

# Define the command to run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]