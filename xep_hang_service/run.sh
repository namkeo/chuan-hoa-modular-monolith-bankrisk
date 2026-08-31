#!/bin/bash

# Define image and container names
IMAGE_NAME="credit-scoring-be"
CONTAINER_NAME="credit-scoring-api"
PORT=8001

echo "=========================================================="
echo "   BUILDING & RUNNING CREDIT SCORING BE AT PORT $PORT     "
echo "=========================================================="

# Stop & remove existing container if running
if [ $(docker ps -aq -f name=^/${CONTAINER_NAME}$) ]; then
    echo "Stopping existing container: ${CONTAINER_NAME}..."
    docker stop ${CONTAINER_NAME}
    docker rm ${CONTAINER_NAME}
fi

# Build Docker image
echo "Building Docker image ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} .

# Run Docker container
echo "Running container ${CONTAINER_NAME} on port ${PORT}..."
docker run -d \
  --name ${CONTAINER_NAME} \
  -p ${PORT}:${PORT} \
  --restart always \
  ${IMAGE_NAME}

echo "=========================================================="
echo "🎉 CONTAINER IS RUNNING AT http://localhost:${PORT}"
echo "📌 API Documentation: http://localhost:${PORT}/docs"
echo "=========================================================="
