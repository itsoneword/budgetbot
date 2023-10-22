#!/bin/bash

# Check if the API_KEY environment variable is set
if [ -z "$API_KEY" ]; then
  echo "API_KEY not provided. The container will now exit."
  exit 1
fi

# Use sed to replace the API_KEY value in the config file
sed -i "s/TOKEN =.*/TOKEN = $API_KEY/" /app/configs/config

python3 core.py