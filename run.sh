#!/bin/bash

# Create virtual environment if none exists
if [ ! -d "./venv" ]; then
    python3 -m venv venv
fi

./venv/bin/python3 ./src/main.py