#!/usr/bin/env python3

import time
import os
import pandas as pd
import glob

# Configure the path and file pattern for CSV files
csv_file_pattern = '/home/deck/*.csv'

# Function to find the latest CSV file based on modification time
def find_latest_csv_file(pattern):
    list_of_files = glob.glob(pattern)
    if not list_of_files:
        return None
    latest_file = max(list_of_files, key=os.path.getmtime)
    return latest_file

# Function to calculate moving average of a list
def moving_average(data, window_size):
    if len(data) < window_size:
        return sum(data) / len(data)
    return sum(data[-window_size:]) / window_size

# Function to take action based on the moving average value
def take_action(moving_avg):
    # This function is a placeholder for the action taken based on the moving average.
    # Implement the specific logic based on your requirements.
    print(f"Moving average of frame time: {moving_avg}")

# Main loop that runs continuously
frametime_window = []
window_size = 5  # The number of samples to consider for the moving average
update_interval = 0.5  # Time interval to update (in seconds)

try:
    while True:
        latest_csv_file = find_latest_csv_file(csv_file_pattern)
        print(f"Latest CSV file: {latest_csv_file}")
        if latest_csv_file:
            # Read the last line of the latest CSV file
            last_line = pd.read_csv(latest_csv_file, skiprows=lambda x: x not in [0,-1], header=None)  # Read only the first and last lines
            frametime = last_line.iloc[-1, 1]  # Assuming the frametime is the second column (index 1)
            frametime_window.append(frametime)  # Append to the frametime window
            print(f"Frame time: {frametime}")   
            # Calculate moving average of frametime
            moving_avg = moving_average(frametime_window, window_size)
            print(f"Moving average of frame time: {moving_avg}")
            # Take action based on moving average value
            take_action(moving_avg)

        # Wait for a specified interval before next update
        time.sleep(update_interval)
except KeyboardInterrupt:
    print("Program stopped by the user.")
except Exception as e:
    print(f"Error: {e}")