#!/bin/bash

# Face-Based Photo Search & Management System Startup Script

echo "Face-Based Photo Search & Management System"
echo "=========================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "Error: pip is not installed or not in PATH"
    echo "Please install pip for Python package management"
    exit 1
fi

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "Current directory: $DIR"

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found"
    exit 1
fi

# Check if virtual environment should be created
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade requirements
echo "Installing/updating requirements..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install requirements"
    echo "You may need to install system dependencies first:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3-dev python3-pip cmake build-essential"
    echo "  sudo apt-get install libopencv-dev python3-opencv"
    exit 1
fi

# Run installation test
echo ""
echo "Running installation test..."
python test_installation.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Installation test failed. Please check the error messages above."
    exit 1
fi

# Start the application
echo ""
echo "Starting the application..."
python main.py

# Deactivate virtual environment
deactivate

echo "Application closed."
