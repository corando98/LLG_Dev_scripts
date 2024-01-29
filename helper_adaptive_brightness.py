#!/usr/bin/env python3
import os

CONTROL_FILE_PATH = '/tmp/adaptive_brightness_control.txt'

commands = {
    'i': 'increase',
    'd': 'decrease',
    'p': 'pause',
    'r': 'resume',
    's': 'reset',
    'h': 'increase_shift',
    'l': 'decrease_shift',
    'e': 'increase_sensitivity',
    't': 'decrease_sensitivity',
    'c': 'print'
}

def write_command_to_file(command):
    try:
        with open(CONTROL_FILE_PATH, 'w') as file:
            file.write(command)
        print(f"Command '{command}' written to {CONTROL_FILE_PATH}")
    except Exception as e:
        print(f"Error writing to file: {e}")

def display_menu():
    print("\nAdaptive Brightness Control CLI")
    print("-------------------------------")
    print("i - Increase Brightness")
    print("d - Decrease Brightness")
    print("p - Pause Adjustments")
    print("r - Resume Adjustments")
    print("s - Reset Settings")
    print("h - Increase Shift")
    print("l - Decrease Shift")
    print("e - Increase Sensitivity")
    print("t - Decrease Sensitivity")
    print("c - Print Current Configuration")
    print("q - Quit")
    print("-------------------------------")

if __name__ == "__main__":
    while True:
        display_menu()
        choice = input("Enter your choice: ").lower()
        if choice == 'q':
            print("Exiting Adaptive Brightness Control CLI")
            break
        elif choice in commands:
            write_command_to_file(commands[choice])
        else:
            print("Invalid choice. Please try again.")
