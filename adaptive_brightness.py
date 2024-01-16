#!/usr/bin/env python3

"""
LtChipotle's Adaptive Brightness Algorithm
==========================================
Improved version.
Modify the following variables to adjust the algorithm:

    
    User variables: 
    - sensitivity_factor: Adjusts how sensitive the algorithm is to changes in light, higher values = steeper curve
    - min_brigthness_level: Adjusts the minimum brightness level, higher values = brighter minimum brightness


    Developer only variables:
    - num_readings: Number of sensor readings to average over
    - max_sensor_value: Maximum sensor value, used to scale the sensor readings
    - backlight_device: Backlight device name, used to locate the brightness file
    - step: Step size to adjust brightness by
    - max_backlight_value: Maximum brightness value, used to cap the brightness
"""


import os
import sys
import logging
from time import sleep
from math import log
from threading import Lock

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

def run_main_loop(backlight_device='amdgpu_bl1', sensitivity_factor=1.0, num_readings=10, max_sensor_value=2752, min_brigthness_level=10):
    lock = Lock()
    als_device = locate_als_device()
    sensor_file1 = f'/sys/bus/iio/devices/{als_device}/in_intensity_both_raw'
    sensor_file2 = f'/sys/bus/iio/devices/{als_device}/in_illuminance_raw'

    readings = []

    while True:
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
                max_sensor_value=max_sensor_value, sensitivity_factor=sensitivity_factor, min_brightness_level=min_brigthness_level)
        sleep(1)

if __name__ == "__main__":
    run_main_loop(
        sensitivity_factor=1, #Adjusts how sensitive the algorithm is to changes in light, higher values = steeper curve
        min_brigthness_level=400) #Adjusts the minimum brightness level, higher values = brighter minimum brightness