#!/usr/bin/env bash

# Install system dependencies
apt-get update && apt-get install -y ffmpeg

# Install Python packages
pip install -r requirements.txt
