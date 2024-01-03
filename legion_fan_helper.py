#!/usr/bin/env python3
"""
Legion Fan Control and Monitoring Script

Description:
    This script is designed to monitor the system's CPU temperature and adjust the fan speed accordingly to ensure optimal cooling and system performance. It implements a hysteresis mechanism to prevent frequent toggling of fan states. The script also logs various system metrics like AC status, Ryzen CPU adjustments, and more for performance monitoring and troubleshooting.

- Monitors CPU temperature
- Adjusts fan speed based on predefined temperature thresholds with hysteresis.
- Logs system performance metrics and hardware sensor readings.
- Checks and logs AC power status and Ryzen CPU limits.

Usage:
    Run the script in a Python environment with necessary permissions. 
    Ensure all dependencies are installed, and the system supports required commands and ACPI calls.
    Use Ctrl+C to stop the script.

Requirements:

psutil - python3 -m pip install psutil
"""


import psutil
import time
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import re

ryzen_monitoring = False

# Configure logging
log_format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)


# File handler for logging
file_handler = RotatingFileHandler("temp_legion_monitor.log", maxBytes=1024*1024*5, backupCount=2)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format))

# Adding file handler to the root logger
logging.getLogger('').addHandler(file_handler)

def get_cpu_temperature():
    temps = psutil.sensors_temperatures()
    for name, entries in temps.items():
        if name.startswith("acpitz"):
            return entries[0].current
def get_ac_status():
    try:
        # Path to the AC power supply status
        ac_status_path = '/sys/class/power_supply/ACAD/online'
        
        with open(ac_status_path, 'r') as file:
            status = file.read().strip()
        
        if status == '1':
            return 'Plugged In'
        else:
            return 'On Battery'
    except IOError:
        logging.error("Failed to read AC status.")
        return None
def get_ryzen_limits():
    command = "ryzenadj -i"
    try:
        result = subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stderr:
            logging.error(f"Error executing Ryzenadj: {result.stderr}")
            return None
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing Ryzenadj command: {e}")
        return None
def format_selected_ryzenadj_output(output):
    # Define the lines of interest
    lines_of_interest = [
        "STAPM LIMIT",
        "STAPM VALUE",
        "PPT LIMIT FAST",
        "PPT VALUE FAST",
        "PPT LIMIT SLOW",
        "PPT VALUE SLOW"
    ]

    # Regex pattern to match the lines containing the relevant data
    pattern = r'\|\s+([\w\s]+)\s+\|\s+([\d\.]+|nan)\s+\|\s+([\w\-]+)?\s+\|'

    # Find all matches
    matches = re.findall(pattern, output)

    # Filtering and formatting the output
    formatted_output = ""
    for match in matches:
        name, value, parameter = match
        if name.strip() in lines_of_interest:
            if parameter:
                formatted_output += f"{parameter.strip()}: {value.strip()} | "
            else:
                formatted_output += f"{name.strip()}: {value.strip()} | "

    return formatted_output
    
def execute_acpi_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Command executed: {command}, Output: {result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {command}, Error: {e.stderr}")
        return None

def set_full_fan_speed(enable):
    """
    Enable or disable full fan speed mode.

    Args:
        enable (bool): True to enable, False to disable.

    Returns:
        str: The result of the operation.
    """
    status = '0x01' if enable else '0x00'
    command = f"echo '\\_SB.GZFD.WMAE 0 0x12 {status}04020000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)

def monitor_and_adjust_fan_speed():
    """
    Monitors the CPU temperature and adjusts the fan speed accordingly.
    Enables full fan speed when the temperature reaches 85°C and disables it when the temperature goes below that threshold.
    """
    TEMPERATURE_THRESHOLD_HIGH = 87  # Temperature to enable full fan speed
    TEMPERATURE_THRESHOLD_LOW = 83   # Temperature to disable full fan speed
    full_speed_enabled = False  # Track the state of full fan speed mode

    try:
        while True:
            cpu_temp = get_cpu_temperature()
            if cpu_temp:
                cpu_temp = int(cpu_temp)
                logging.info(f"CPU Temperature: {cpu_temp}°C")

                if cpu_temp >= TEMPERATURE_THRESHOLD_HIGH and not full_speed_enabled:
                    logging.info("High temperature detected. Enabling full fan speed.")
                    set_full_fan_speed(True)
                    full_speed_enabled = True
                elif cpu_temp <= TEMPERATURE_THRESHOLD_LOW and full_speed_enabled:
                    logging.info("Temperature back to normal. Disabling full fan speed.")
                    set_full_fan_speed(False)
                    full_speed_enabled = False

            else:
                logging.error("Could not read CPU temperature")

            ac_status = get_ac_status()
            if ac_status:
                logging.info(f"AC Status: {ac_status}")

            if ryzen_monitoring:
                ryzen_limits = get_ryzen_limits()
                if ryzen_limits:
                    ryzen_limits = format_selected_ryzenadj_output(ryzen_limits)
                    logging.info(f"Ryzen Limits: {ryzen_limits}")


            time.sleep(5)  # Check temperature every 5 seconds
    except KeyboardInterrupt:
        print("Monitoring stopped.")

if __name__ == "__main__":
    monitor_and_adjust_fan_speed()
