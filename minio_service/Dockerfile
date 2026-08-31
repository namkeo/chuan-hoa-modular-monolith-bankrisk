# Custom MinIO Entrypoint Dockerfile for Bank System Risk Analysis
FROM minio/minio:latest

# Environment defaults
ENV MINIO_ROOT_USER=minioadmin
ENV MINIO_ROOT_PASSWORD=minioadminpassword

# Expose S3 API port (9000) and Console port (9001)
EXPOSE 9000 9001

# Entrypoint running MinIO server with console enabled
CMD ["server", "/data", "--console-address", ":9001"]
