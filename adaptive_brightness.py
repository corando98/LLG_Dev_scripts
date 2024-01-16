#!/usr/bin/env python3

"""
LtChipotle's Adaptive Brightness Algorithm
==========================================
Improved version.
Modify the following variables to adjust the algorithm:

    
    User variables: 
    - sensitivity_factor: Adjusts how sensitive the algorithm is to changes in light, higher values = steeper curve
    - min_brigthness_level: Adjusts the minimum brightness level, higher values = brighter minimum brightness
    - pause: Pause brightness adjustments
    - silent: Silence all logging

    
    
    Developer only variables: (Use these only if you know what you're doing)
    - num_readings: Number of sensor readings to average over
    - max_sensor_value: Maximum sensor value, used to scale the sensor readings
    - backlight_device: Backlight device name, used to locate the brightness file
    - step: Step size to adjust brightness by
    - max_backlight_value: Maximum brightness value, used to cap the brightness
"""

# Recommended command: ./adaptive_brightness.py --min_brightness_level 400 --sensitivity_factor 1.0

import os
import sys
import logging
from time import sleep
from math import log
from threading import Lock
import argparse


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_brightness_from_sensor(sensor_value, max_sensor_value=2752, sensitivity_factor=1.0, min_brightness_level=10):
    if sensor_value <= 0:
        return min_brightness_level # Return minimum brightness if sensor value is non positive
    # Apply log fun to scale the sensor value
    adjusted_value = log(sensor_value) * sensitivity_factor
    # Scale the adjusted value to [0, 1], then multiply by the max sensor range, and add the minimum level
    return max(min_brightness_level, int(adjusted_value / log(max_sensor_value) * (max_sensor_value - min_brightness_level) + min_brightness_level))

def read_brightness(backlight_device):
    brightness_path = f'/sys/class/backlight/{backlight_device}/brightness'
    try:
        with open(brightness_path, 'r') as file:
            return int(file.read().strip())
    except OSError as e:
        logging.error(f"Failed to read brightness: {e}")
        sys.exit(1)

def write_brightness(backlight_device, brightness, max_backlight_value=4095):
    brightness_path = f'/sys/class/backlight/{backlight_device}/brightness'
    brightness = max(0, min(brightness, max_backlight_value))
    try:
        with open(brightness_path, 'w') as file:
            file.write(str(brightness))
    except OSError as e:
        logging.error(f"Failed to write brightness: {e}")
        return False
    return True

def adjust_display_brightness(sensor_reading, backlight_device, max_sensor_value=2752, max_backlight_value=4095, step=10, sensitivity_factor=1.0, min_brightness_level=10):
    logging.debug("Adjusting display brightness")
    
    target_brightness = calculate_brightness_from_sensor(sensor_reading, max_sensor_value, sensitivity_factor, min_brightness_level)
    logging.debug(f"Target brightness: {target_brightness}")

    current_brightness = read_brightness(backlight_device)
    logging.debug(f"Current brightness: {current_brightness}")

    step_value = step if target_brightness > current_brightness else -step
    new_brightness = current_brightness

    while abs(target_brightness - new_brightness) >= step:
        new_brightness += step_value
        if not write_brightness(backlight_device, new_brightness, max_backlight_value):
            break
        logging.debug(f"Adjusting brightness: {new_brightness}")
        sleep(0.05) #smoothen transition

    if not write_brightness(backlight_device, target_brightness, max_backlight_value):
        logging.error("Failed to set brightness")
    else:
        logging.debug(f"Brightness adjusted to: {target_brightness}")
    

def locate_als_device():
    iio_path = '/sys/bus/iio/devices/'
    try:
        for device_dir in os.listdir(iio_path):
            if device_dir.startswith('iio:device'):
                device_name_path = os.path.join(iio_path, device_dir, 'name')
                with open(device_name_path, 'r') as file:
                    if file.read().strip() == 'als':
                        return device_dir
    except OSError as e:
        logging.error(f"Failed to locate ALS device: {e}")

    logging.error('ALS device not found')
    sys.exit(1)

def run_main_loop(backlight_device, sensitivity_factor, num_readings, max_sensor_value, min_brightness_level, pause):
    lock = Lock()
    als_device = locate_als_device()
    sensor_file1 = f'/sys/bus/iio/devices/{als_device}/in_intensity_both_raw'
    sensor_file2 = f'/sys/bus/iio/devices/{als_device}/in_illuminance_raw'

    readings = []

    while True:
        if not pause:
            try:
                with open(sensor_file1, 'r') as file:
                    intensity = int(file.read().strip())
                with open(sensor_file2, 'r') as file:
                    illuminance = int(file.read().strip())
            except OSError as e:
                logging.error(f"Failed to read sensor data: {e}")
                continue

            average_reading = (intensity + illuminance) // 2
            readings.append(average_reading)
            readings = readings[-num_readings:]

            moving_average = sum(readings) / len(readings)
            logging.debug(f"Moving average: {moving_average}")
            with lock:
                adjust_display_brightness(
                    moving_average, 
                    backlight_device, 
                    max_sensor_value=max_sensor_value, sensitivity_factor=sensitivity_factor, min_brightness_level=min_brightness_level)
            sleep(1)
        else:
            logging.debug("Brightness adjustments paused")
            sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LtChipotle's Adaptive Brightness Algorithm with command line arguments.")
    parser.add_argument('--min_brightness_level', type=int, default=200, help='The minimum brightness level to be set.')
    parser.add_argument('--sensitivity_factor', type=float, default=1.0, help='The sensitivity factor for brightness adjustment.')
    parser.add_argument('--pause', action='store_true', help='Pause brightness adjustments.')

    parser.add_argument('--num_readings', type=int, default=10, help='The number of sensor readings to average. DEV')
    parser.add_argument('--backlight_device', type=str, default='amdgpu_bl1', help='The backlight device to control.')
    parser.add_argument('--max_sensor_value', type=int, default=2752, help='The maximum sensor value for brightness scaling. DEV')
    parser.add_argument('--silent', action='store_true', help='Silence all logging.')
    args = parser.parse_args()

    if args.silent:
        logging.disable(logging.CRITICAL)

    run_main_loop(
        backlight_device=args.backlight_device,
        sensitivity_factor=args.sensitivity_factor,
        num_readings=args.num_readings,
        max_sensor_value=args.max_sensor_value,
        min_brightness_level=args.min_brightness_level,
        pause=args.pause
    )