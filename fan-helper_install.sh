#!/bin/bash

# Get the directory where the install.sh script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Define the path to the Python script
SCRIPT_PATH="$SCRIPT_DIR/legion_fan_helper.py"

# Define the service file content
SERVICE_FILE_CONTENT="[Unit]
Description=Legion Go Fan helper method

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH --temp_high 85 --temp_low 80 --logging True
Restart=always
User=$(whoami)
Environment=\"PATH=/usr/bin:/bin\"

[Install]
WantedBy=multi-user.target"

# Define the location where the service file will be created
SERVICE_FILE="/etc/systemd/system/legion_fan_helper.service"

# Check if running as root
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

# Check for pip and install if it's not installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 could not be found, installing..."
    apt-get update && apt-get install python3-pip -y
fi

# Install psutil
echo "Installing psutil..."
pip3 install psutil

# Create the service file
echo "$SERVICE_FILE_CONTENT" > $SERVICE_FILE

# Reload systemd to recognize the new service
systemctl daemon-reload

# Enable and start the service
systemctl enable legion_fan_helper.service
systemctl start legion_fan_helper.service

echo "Service installed and started successfully."
