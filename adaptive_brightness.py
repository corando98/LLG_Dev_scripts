#!/usr/bin/env python3

"""
LtChipotle's Adaptive Brightness Algorithm
==========================================
This algorithm is designed to be used with Legion Go ALS (Ambient Light Sensor), it uses the sensor readings to calculate the brightness of the display. The algorithm is based on the inverse logarithmic function, which is used to calculate the brightness byte value. The byte value is then scaled to the display's brightness range and the brightness is changed gradually to avoid flickering. The algorithm is designed to be used with the Legio Go, but it can be easily adapted to other displays by changing the max_sensor_value and max_backlight_value parameters. 

The algorithm is based on the following formula:
    y = 19.811 * ln(x) - 9.411
where x is the sensor reading and y is the brightness byte value. The formula is derived from the following formula:
    y = 255 * ln(x) / ln(2752)


    To adjust the sensitivity of the algorithm, you can change the sensitivity_factor parameter. The default value is 1.0, the sensitivity_factor value can be any positive number, but it is recommended to keep it between 0.5 and 2.0.
"""
import os
import sys
from time import sleep
import numpy as np
from threading import Lock
import logging

lock = Lock()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def inverse_log_function(y, max_sensor_value=2752, sensitivity_factor=1.0):
    if y <= 0:
        return 1  # Return the minimum brightness byte value if the result is non-positive
    adjusted_y = y * sensitivity_factor
    return np.exp((adjusted_y + 9.411) / 19.811)

def get_current_brightness(backlight_device):
    brightness_file = f'/sys/class/backlight/{backlight_device}/brightness'
    with open(brightness_file, 'r') as file:
        return int(file.read().strip())

def set_brightness(backlight_device, brightness):
    brightness_file = f'/sys/class/backlight/{backlight_device}/brightness'
    with open(brightness_file, 'w') as file:
        file.write(str(brightness))

def set_display_brightness(average_reading, backlight_device, max_backlight_value=4095, step=10, sensitivity_factor=1.0):
    # Read sensor data
    logging.info("Starting to set display brightness")
    
    # Use the inverse logarithmic function to calculate the brightness byte value
    brightness_byte_value = inverse_log_function(average_reading, max_sensor_value=2752, sensitivity_factor=sensitivity_factor)

    # Scale the byte value to the display's brightness range
    target_brightness = int((brightness_byte_value / 2752) * max_backlight_value)
    
    # Ensure the target value is within the valid range
    target_brightness = max(1, min(max_backlight_value, target_brightness))

    # Get the current brightness
    current_brightness = get_current_brightness(backlight_device)

    # Calculate the difference
    difference = target_brightness - current_brightness

    # Determine the step value
    step_value = step if difference > 0 else -step

    # Change the brightness gradually
    new_brightness = current_brightness
    while abs(difference) >= step:
        new_brightness += step_value
        set_brightness(backlight_device, new_brightness)
        difference = target_brightness - new_brightness
        sleep(0.1)  # sleep for 100ms
        logging.info(f"Current brightness: {new_brightness}")

    # Set the final target brightness
    set_brightness(backlight_device, target_brightness)
    logging.info(f"Finished setting brightness. New brightness: {new_brightness}")

def find_als_device():
    iio_path = '/sys/bus/iio/devices/'
    print(f'Looking for ALS device in {iio_path}')
    for device_dir in os.listdir(iio_path):
        if device_dir.startswith('iio:device'):
            with open(os.path.join(iio_path, device_dir, 'name'), 'r') as file:
                if file.read().strip() == 'als':
                    return device_dir
    raise RuntimeError('ALS device not found')

def main_loop(sensitivity_factor=1.0):
    als_device = find_als_device()
    sensor_file1 = f'/sys/bus/iio/devices/{als_device}/in_intensity_both_raw'
    sensor_file2 = f'/sys/bus/iio/devices/{als_device}/in_illuminance_raw'
    backlight_device = 'amdgpu_bl1'  # Update this if necessary

    readings = []
    num_readings = 10
    

    while True:
        with open(sensor_file1, 'r') as file:
            intensity = int(file.read().strip())
        with open(sensor_file2, 'r') as file:
            illuminance = int(file.read().strip())
        average_reading = (intensity + illuminance) // 2
        readings.append(average_reading)
        readings = readings[-num_readings:]

        moving_average = sum(readings) / len(readings)
        logging.info(f"Moving average: {moving_average}")
        with lock:
            set_display_brightness(moving_average, backlight_device, sensitivity_factor=sensitivity_factor)
        sleep(1)

        

# Make sure the main loop runs directly
if __name__ == "__main__":
    main_loop()