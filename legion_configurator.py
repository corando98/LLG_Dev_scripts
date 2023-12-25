import hid
import time
# Global variables
vendor_id = 0x17EF
product_id_match = lambda x: x & 0xFFF0 == 0x6180
usage_page = 0xFFA0
global_config = None

"""
This file contains functions to send commands to the Legion Go controller.
"""

def get_config():
    global global_config

    try:
        # Enumerate and set the global configuration
        for dev in hid.enumerate(vendor_id):
            if product_id_match(dev["product_id"]) and dev["usage_page"] == usage_page:
                global_config = dev
                break
    except Exception as e:
        print("legion_configurator error: couldn't find device config")

    if not global_config:
        print("Legion go configuration device not found.")
    else:
        print(global_config)

def send_command(command):
    global global_config
    get_config()
    assert len(command) == 64 and global_config
    try:
        with hid.Device(path=global_config['path']) as device:
            device.write(command)
            print("Command sent successfully.")
    except IOError as e:
        print(f"Error opening HID device: {e}")


def create_touchpad_command(enable):
    """
    Create a command to enable or disable the touchpad.

    :param enable: bool - True to enable, False to disable the touchpad
    :return: bytes - The command byte array
    """
    enable_byte = 0x01 if enable else 0x00

    command = [
        0x05,
        0x06,  # Report ID and Length
        0x6B,  # Command (Nibble 6 + b)
        0x02,  # Command sub-parameter
        0x04,  # Right Controller
        enable_byte,  # Enable/Disable flag
        0x01   # All commands end with 0x01
    ]

    byte_command = bytes(command)
    # Pad the byte_command with 0xCD to meet the length of 64 bytes
    buffered_command = byte_command + bytes([0xCD] * (64 - len(byte_command)))
    return buffered_command

def create_rgb_control_command(controller, mode, color, brightness, speed, profile=0x01, on=True):
    """
    Create a command to control the RGB LEDs, including setting the profile and turning them on or off.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param mode: byte - The mode of the LED (e.g., 0x01 for solid, 0x02 for blinking)
    :param color: bytes - The RGB color value (e.g., b'\xFF\x00\x00' for red)
    :param brightness: byte - The brightness value (0x00 to 0x64)
    :param speed: byte - The speed setting for dynamic modes (0x00 to 0x64, higher is slower)
    :param profile: byte - The profile number
    :param on: bool - True to turn on, False to turn off the RGB LEDs
    :return: bytes - The command byte array
    """
    on_off_byte = 0x01 if on else 0x00
    command = [
        0x05, 0x0c if on else 0x06,  # Report ID and Length (0x0c for setting profile, 0x06 for on/off)
        0x72 if on else 0x70,        # Command (Nibble 7 + 2 for profile, 7 + 0 for on/off)
        0x01, controller
    ]

    if on:
        # Adding profile settings when turning on
        command += [mode] + list(color) + [brightness, speed, profile, 0x01]
    else:
        # Adding the on/off byte when turning off
        command += [on_off_byte, 0x01]

    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_rgb_on_off_command(controller, on):
    """
    Create a command to turn the RGB LEDs on or off.

    :param controller: byte - The controller byte (e.g., 0x03 for left, 0x04 for right)
    :param on: bool - True to turn on, False to turn off
    :return: bytes - The command byte array
    """
    on_off_byte = 0x01 if on else 0x00
    command = [
        0x05, 0x06,  # Report ID and Length
        0x70,        # Command (Nibble 7 + 0)
        0x02,        # Sub-parameter
        controller,  # Controller
        on_off_byte, # On/Off
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_gyro_remap_command(gyro, joystick):
    """
    Create a command for gyro remapping.

    :param gyro: byte - The gyro setting (e.g., 0x01, 0x02)
    :param joystick: byte - The joystick value (e.g., 0x00, 0x01, 0x02)
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x08,  # Report ID and Length
        0x6a,        # Command (Nibble 6 + a)
        0x06, 0x01, 0x01,  # Sub-parameters
        gyro, joystick,
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_button_remap_command(controller, button, action):
    """
    Create a command for button remapping.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param button: byte - The button to remap. Button codes:
                    0x1c: Y1, 0x1d: Y2, 0x1e: Y3, 0x21: M2, 0x22: M3
    :param action: byte - The action to assign to the button. Action codes:
                   0x00: Disabled, 0x03: Left Stick Click, 0x04: Left Stick Up,
                   0x05: Left Stick Down, 0x06: Left Stick Left, 0x07: Left Stick Right,
                   0x08: Right Stick Click, 0x09: Right Stick Up, 0x0a: Right Stick Down,
                   0x0b: Right Stick Left, 0x0c: Right Stick Right, 0x0d: D-Pad Up,
                   0x0e: D-Pad Down, 0x0f: D-Pad Left, 0x10: D-Pad Right,
                   0x12: A, 0x13: B, 0x14: X, 0x15: Y, 0x16: Left Bumper,
                   0x17: Left Trigger, 0x18: Right Bumper, 0x19: Right Trigger,
                   0x23: View, 0x24: Menu
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x07,  # Report ID and Length
        0x6c,        # Command (Nibble 6 + c)
        0x02, controller, button, action,
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_vibration_command(controller, vibration_level):
    """
    Create a command to control the vibration of the controller.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param vibration_level: byte - Vibration level (0x00: Off, 0x01: Weak, 0x02: Medium, 0x03: Strong)
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x06,  # Report ID and Length
        0x67,        # Command (Nibble 6 + 7)
        0x02,        # Sub-parameter
        controller, vibration_level,
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_fps_remap_command(controller, profile, button, action):
    """
    Create a command for FPS remapping.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param profile: byte - The profile number (from 0x01 to 0x04)
    :param button: byte - The button to remap
    :param action: byte - The action to assign to the button
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x08,  # Report ID and Length
        0x6c,        # Command (Nibble 6 + c)
        0x04,        # Sub-parameter
        controller, profile, button, action,
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_sleep_time_command(controller, time_in_minutes):
    """
    Create a command to set the sleep time of the controller.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param time_in_minutes: byte - Sleep time in minutes
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x06,  # Report ID and Length
        0x33,        # Command
        0x01,        # Sub-parameter
        controller, time_in_minutes,
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

# Redundant function
def create_gyro_enable_command(controller, enable):
    """
    Create a command to enable or disable the gyro on the controller.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param enable: byte - Enable (0x01) or disable (0x00) the gyro
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x08,  # Report ID and Length
        0x6a,        # Command
        0x02,        # Sub-parameter
        controller, enable,
        0x01         # Command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_touchpad_vibration_command(enable):
    """
    Create a command to enable or disable touchpad vibration.

    :param enable: bool - True to enable, False to disable touchpad vibration
    :return: bytes - The command byte array
    """
    enable_byte = 0x02 if enable else 0x01
    command = [
        0x05, 0x06,  # Report ID and Length
        0x6b, 0x04, 0x04,  # Command and sub-parameters
        enable_byte, 0x01   # Enable/Disable flag and command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_legion_button_swap_command(enable):
    """
    Create a command to swap legion buttons with start/select.

    :param enable: bool - True to swap, False to revert
    :return: bytes - The command byte array
    """
    enable_byte = 0x02 if enable else 0x01
    command = [
        0x05, 0x06,  # Report ID and Length
        0x69, 0x04, 0x01,  # Command and sub-parameters
        enable_byte, 0x01   # Enable/Disable flag and command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_deadzone_command(controller, level):
    """
    Create a command to control the deadzones of the sticks.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param level: byte - Deadzone level (0x00 to 0x63, default is 0x04)
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x06,  # Report ID and Length
        0x3f, 0x06,  # Command and sub-parameter
        controller, level, 0x01  # Controller, level and command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_sensitivity_command(controller, tx, ty, bx, by):
    """
    Create a command to control the sensitivity of the sticks.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param tx, ty, bx, by: byte - Sensitivity settings
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x09,  # Report ID and Length
        0x3f, 0x02,  # Command and sub-parameter
        controller, tx, ty, bx, by, 0x01  # Controller, sensitivity settings, and command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

# sleepLeft = create_sleep_time_command(0x03, 0x01)
# sleepRight = create_sleep_time_command(0x04, 0x01)

# send_command(sleepLeft)
# send_command(sleepRight)    
# print("Sleep time set to 1 minute.")

# # Enable touchpad vibration
# touchpad_vibration_command = create_touchpad_vibration_command(True)
# send_command(touchpad_vibration_command)
# # Swap legion buttons with start/select
# legion_button_swap_command = create_legion_button_swap_command(True)
# send_command(legion_button_swap_command)
# # Set deadzone for left stick to 10%
# left_stick_deadzone_command = create_deadzone_command(0x03, 0x64)
# send_command(left_stick_deadzone_command)
# # Adjust sensitivity for right stick (example values)
# right_stick_sensitivity_command = create_sensitivity_command(0x04, 0x10, 0x15, 0x0A, 0x0F)
# send_command(right_stick_sensitivity_command)
