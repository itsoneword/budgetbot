#!/bin/bash
set -e

# Check if the API_KEY environment variable is set
if [ -z "$API_KEY" ]; then
  echo "API_KEY not provided. The container will now exit."
  exit 1
fi

echo "Starting budgetbot with provided API_KEY..."

# Make sure the config directory exists
if [ ! -d "/app/configs" ]; then
  echo "Creating configs directory..."
  mkdir -p /app/configs
fi

# Use sed to replace the API_KEY value in the config file
if [ -f "/app/configs/config" ]; then
  echo "Updating TOKEN in config file..."
  sed -i "s/TOKEN =.*/TOKEN = $API_KEY/" /app/configs/config
else
  echo "Config file not found. Creating new config file..."
  echo "[TELEGRAM]" > /app/configs/config
  echo "TOKEN = $API_KEY" >> /app/configs/config
fi

# Check if run.py exists first, as that's the intended entry point
if [ -f "/app/run.py" ]; then
  echo "Running run.py..."
  python3 /app/run.py

else
  echo "ERROR: Could not find run.py or core.py in /app or /app/src directories!"
  echo "Contents of /app directory:"
  ls -la /app
  echo "Contents of /app/src directory (if it exists):"
  ls -la /app/src 2>/dev/null || echo "/app/src directory does not exist"
  exit 1
fi