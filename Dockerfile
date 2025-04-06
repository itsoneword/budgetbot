FROM python:3.9-slim AS builder

# Set up pip to be faster and more efficient
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy just the requirements file first to leverage Docker cache
COPY requirements.txt /tmp/
RUN pip install --user --no-warn-script-location -r /tmp/requirements.txt

# Final stage
FROM python:3.9-slim

# Copy the installed packages from the builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install only the necessary system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy only necessary files and directories
COPY run.py /app/
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY entrypoint.sh /app/

# Ensure entrypoint script has correct line endings and permissions
RUN dos2unix /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh


# Set the entrypoint
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
