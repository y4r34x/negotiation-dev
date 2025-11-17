#!/bin/bash

# Run FastAPI app with uvicorn
# To make this script executable, run: chmod +x run.sh

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set Bluesky API credentials
export BLUESKY_HANDLE="moonlightdiplomacy@gmail.com"
export BLUESKY_PASSWORD="7hkqhzcHXH8us5X"

uvicorn main:app --host 0.0.0.0 --port 8000

