#!/usr/bin/env python3

"""
LtChipotle's Adaptive Brightness Algorithm
==========================================
Improved version.
Modify the following variables to adjust the algorithm:

    
    User variables: 
    - sensitivity_factor: Adjusts how sensitive the algorithm is to changes in light, higher values = steeper curve
    - min_brigthness_level: Adjusts the minimum brightness level, higher values = brighter minimum brightness
    - step: Step size to adjust brightness by
    - pause: Pause brightness adjustments
    - silent: Silence all logging

    To adjust the algorithm to your liking play with:
    - sensitivity_factor, min_brightness_level, step


    Some profiles, which are not implemented yet, but can be used as a reference:
    PROFILE_CONFIGS = {
    'reading': {'sensitivity_factor': 0.8, 'min_brightness_level': 100, 'step': 50},
    'day': {'sensitivity_factor': 1.5, 'min_brightness_level': 200, 'step': 100},
    'evening': {'sensitivity_factor': 1.2, 'min_brightness_level': 50, 'step': 50},
    'movie': {'sensitivity_factor': 0.5, 'min_brightness_level': 80, 'step': 20},
    'night': {'sensitivity_factor': 0.3, 'min_brightness_level': 10, 'step': 30},
    }   

Reading Mode:
    Smoother adjustments are fine here because users will not expect quick changes in ambient light when focused on reading.
    Proposed step: 50 (reduces the full-scale adjustment time to about 8 seconds)
Day Mode:
    During the day, users might expect quicker adjustments.
    Proposed step: 100 (reduces the full-scale adjustment time to about 4 seconds)
Evening Mode:
    Evening light changes can be more gradual, so a moderate speed is suitable.
    Proposed step: 50
Movie Mode:
    Avoiding distractions is key, so the slowest and smoothest transitions are ideal.
    Proposed step: 20 (still relatively smooth but a bit quicker to react)
Night Mode:
    Brightness should not change rapidly during the night to avoid disturbing users.
    Proposed step: 30 (smooth adjustments without being too slow)

    


    Developer only variables: (Use these only if you know what you're doing)
    - num_readings: Number of sensor readings to average over
    - max_sensor_value: Maximum sensor value, used to scale the sensor readings
    - backlight_device: Backlight device name, used to locate the brightness file
    - max_backlight_value: Maximum brightness value, used to cap the brightness

    Example systemd service file: (Replace /path/to/ with the actual path to the script)
    location example '/etc/systemd/system/adaptive_brightness.service'

    '''
    [Unit]
    Description=Adaptive Brightness Service
    After=network.target

    [Service]
    Type=simple
    ExecStart=/path/to/adaptive_brightness.py start --min_brightness_level 400 --sensitivity_factor 1.0
    ExecStop=/path/to/adaptive_brightness.py pause 
    ExecReload=/path/to/adaptive_brightness.py resume
    User=your_username
    Restart=on-failure
    RestartSec=5s
    [Install]
    WantedBy=multi-user.target

    '''

    Then run the following commands:

    sudo systemctl daemon-reload
    sudo systemctl enable --now adaptive-brightness.service

    sudo systemctl stop adaptive-brightness.service   # This will run the pause subcommand
    sudo systemctl start adaptive-brightness.service  # This will run the start subcommand
    sudo systemctl reload adaptie-brightness.service  # This will run the resume subcommand


    Sysfs control files:
    
    /tmp/adaptive_brightness_pause.flag: Pause flag file, if this file exists, the service will pause brightness adjustments.

    example: touch /tmp/adaptive_brightness_pause.flag # This will pause brightness adjustments
                rm /tmp/adaptive_brightness_pause.flag   # This will resume brightness adjustments


"""
# Constant for pause flag file
PAUSE_FLAG_FILE_PATH = '/tmp/adaptive_brightness_pause.flag'

# Constants for stability detection\

# This is delta value for the moving average to be considered stable, if the delta is within this value for STABILITY_DURATION amount of time, the cooldown will be increased to reduce constant brightness changes, flickering, etc. This also prevents the brightness from changing too quickly, and applies hysterisis.
STABILITY_THRESHOLD = 5  
# The amount of time the moving average has to be stable for before the cooldown is increased.
STABILITY_DURATION = 60  
# The value of STABILITY_DURATION set to 60 indicates the duration (in seconds) the moving average has to remain stable within the STABILITY_THRESHOLD before the cooldown period is increased. This is separate from the maximum cooldown period, which is the longest delay between subsequent brightness adjustments when the moving average is stable.

import os
import sys
import logging
import time
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

    # Smaller sleep time for quicker adjustments or larger for smoother adjustments
    adjustment_interval = 0.05 if step > 50 else 0.1

    while abs(target_brightness - new_brightness) >= step:
        new_brightness += step_value
        if not write_brightness(backlight_device, new_brightness, max_backlight_value):
            break
        logging.debug(f"Adjusting brightness: {new_brightness}")
        sleep(adjustment_interval) #smoothen transition

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
                        logging.debug(f"Found ALS device: {device_dir}")
                        return device_dir
    except OSError as e:
        logging.error(f"Failed to locate ALS device: {e}")

    logging.error('ALS device not found')
    sys.exit(1)

def locate_backlight_device():
    backlight_base_path = '/sys/class/backlight/'
    try:
        devices = os.listdir(backlight_base_path)
        if devices:
            logging.debug(f"Found backlight devices: {devices}")
            return devices[0]  # Return the first found backlight device
        else:
            logging.error('No backlight devices found.')
            sys.exit(1)
    except OSError as e:
        logging.error(f"Failed to locate backlight device: {e}")
        sys.exit(1)


def run_main_loop(backlight_device, sensitivity_factor, num_readings, max_sensor_value, min_brightness_level, pause, stability_threshold=STABILITY_THRESHOLD, stability_duration=STABILITY_DURATION, step=10):
    lock = Lock()
    als_device = locate_als_device()
    sensor_file1 = f'/sys/bus/iio/devices/{als_device}/in_intensity_both_raw'
    sensor_file2 = f'/sys/bus/iio/devices/{als_device}/in_illuminance_raw'

    readings = []

    last_change_time = time.monotonic()
    stable_value = None
    cooldown_period = 1 # Start with 1 second cooldown period


    while True:
        if os.path.exists(PAUSE_FLAG_FILE_PATH):
            logging.info("Brightness adjustment is paused due to flag file at {}".format(PAUSE_FLAG_FILE_PATH))
            sleep(5)
            continue
        if not pause:
            try:
                with open(sensor_file1, 'r') as file:
                    intensity = int(file.read().strip())
                # with open(sensor_file2, 'r') as file:
                #     illuminance = int(file.read().strip())
            except OSError as e:
                logging.error(f"Failed to read sensor data: {e}")
                continue

            # average_reading = (intensity + illuminance) // 2
            average_reading = intensity
            readings.append(average_reading)
            readings = readings[-num_readings:]

            moving_average = sum(readings) / len(readings)
            logging.debug(f"Moving average: {moving_average}")
            if stable_value is not None:
                logging.debug(f"Stability delta: {abs(moving_average - stable_value)}")
            if stable_value is None or abs(moving_average - stable_value) > stability_threshold:
                stable_value = moving_average
                last_change_time = time.monotonic()
                cooldown_period = 1 # Reset cooldown period to 1 second
                logging.debug(f"Resetting cooldown period: {cooldown_period}")
            elif (time.monotonic() - last_change_time) >= stability_duration:
                # If the value has been stable for longer than STABILITY_DURATION, increase cooldown period
                cooldown_period = min(cooldown_period * 2, 30)  # Maximum cooldown period of 30 seconds
                logging.debug(f"Increasing cooldown period: {cooldown_period}")
            if cooldown_period == 1 or time.monotonic() - last_change_time < stability_duration:
                # Change brightness if not in cooldown or within the stability duration
                with lock:
                    adjust_display_brightness(
                        moving_average, 
                        backlight_device, 
                        max_sensor_value=max_sensor_value, 
                        sensitivity_factor=sensitivity_factor, 
                        min_brightness_level=min_brightness_level,
                        step=step)
            logging.debug(f"Cooldown period: {cooldown_period}")
            sleep(cooldown_period)
        else:
            logging.debug("Brightness adjustments paused")
            sleep(5)

def start_service(args):
    run_main_loop(
        backlight_device=args.backlight_device,
        sensitivity_factor=args.sensitivity_factor,
        num_readings=args.num_readings,
        max_sensor_value=args.max_sensor_value,
        min_brightness_level=args.min_brightness_level,
        pause=False,
        step=args.step
    )

def pause_service(args):
    # Create a flag file to signal that the service should pause.
    with open(PAUSE_FLAG_FILE_PATH, 'w') as f:
        pass  # The existence of the file is the pause flag; it can be empty.
    logging.info("Adaptive brightness adjustment paused. File created: /tmp/adaptive_brightness_pause.flag")
    pass

def resume_service(args):
    # Remove the flag file to signal that the service should resume.
    try:
        os.remove(PAUSE_FLAG_FILE_PATH)
        logging.info("Adaptive brightness adjustment resumed. File removed: /tmp/adaptive_brightness_pause.flag")
    except FileNotFoundError:
        logging.warning("Adaptive brightness adjustment was not paused.")
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LtChipotle's Adaptive Brightness Algorithm")
    subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')

    backlight_device_default = locate_backlight_device()

    # Start service subcommand
    parser_start = subparsers.add_parser('start', help='Start the adaptive brightness service.')
    parser_start.add_argument('--min_brightness_level', type=int, default=400, help='The minimum brightness level to be set.')
    parser_start.add_argument('--sensitivity_factor', type=float, default=1.0, help='The sensitivity factor for brightness adjustment.')
    parser_start.add_argument('--step', type=int, default=50, help='The step size to adjust brightness by.')
    parser_start.add_argument('--silent', action='store_true', help='Silence all logging.')
    parser_start.add_argument('--backlight_device', type=str, default=backlight_device_default, help='The backlight device to control. (DEV)')
    parser_start.add_argument('--num_readings', type=int, default=10, help='The number of sensor readings to average. (DEV)')
    parser_start.add_argument('--max_sensor_value', type=int, default=2752, help='The maximum sensor value for brightness scaling. (DEV)')
    parser_start.set_defaults(func=start_service)
    if parser_start.parse_known_args()[0].silent:
        logging.disable(logging.CRITICAL)

    # Pause service subcommand
    parser_pause = subparsers.add_parser('pause', help='Pause the adaptive brightness service.')
    parser_pause.set_defaults(func=pause_service)

    # Resume service subcommand
    parser_resume = subparsers.add_parser('resume', help='Resume the adaptive brightness service.')
    parser_resume.set_defaults(func=resume_service)

    args = parser.parse_args()
    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()