#!/bin/python3
import hid
import time
import argparse
import sys
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

def send_command(command, read_response=False):
    global global_config
    get_config()
    assert len(command) == 64 and global_config
    try:
        with hid.Device(path=global_config['path']) as device:
            device.write(command)
            print("Command sent successfully.")
            if read_response:
                response = device.read(64)  # Assuming response is 64 bytes
                print("Response received:", response)
                return response
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
    Two point calibration is used for the sensitivity settings.
    This is esentiall the curve, where the "curve" is made up of two points.
    t = top, b = bottom, x = x-axis, y = y-axis, tx > bx and ty > by
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

"""
Getter functions for the controller settings. (untested)
"""
def create_leds_command(controller):
    """
    Create a command for LEDs settings.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x05,  # Report ID and Length
        0x6a, 0x01,  # Command and sub-parameter
        controller, 0x01  # Controller and command end marker
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_vibration_sensitivity_command():
    """
    Create a command related to vibration/sensitivity settings.
    
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x06,  # Report ID and Length
        0x83, 0x01,  # Command and sub-parameter
        0x01, 0x02, 0x01  # Additional settings
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))
def create_vibration_sensitivity_command():
    """
    Create a command related to vibration/sensitivity settings.
    
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x06,  # Report ID and Length
        0x83, 0x01,  # Command and sub-parameter
        0x01, 0x02, 0x01  # Additional settings
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
    
def controller_mapping(value):
    mapping = {
        'left': 0x03,
        'right': 0x04
    }
    print(value.lower())  
    print(mapping[value.lower()])  
    if value.lower() in mapping:
        return mapping[value.lower()]
    else:
        raise argparse.ArgumentTypeError('Invalid controller. Use "left" or "right".')
def main():
    parser = argparse.ArgumentParser(description='Legion Controller Configurator Script')

    # Argument for touchpad vibration
    parser.add_argument('--touchpad-vibration', type=str2bool, default=None, 
                        metavar=('bool'),
                        help='Enable or disable touchpad vibration (True/False), example: --touchpad-vibration True')
    # Argument for RGB control
    parser.add_argument('--rgb-control', nargs=6, metavar=('CONTROLLER', 'MODE', 'COLOR', 'BRIGHTNESS', 'SPEED', 'PROFILE'),
                        help='Control RGB settings: controller ("left" or "right"), mode (byte), color (R G B), brightness (byte), speed (byte), profile (byte)')

    # Argument for gyro remap
    parser.add_argument('--gyro-remap', nargs=2, metavar=('GYRO', 'JOYSTICK'),
                        help='Set gyro remapping: gyro setting (byte), joystick value (byte), left controller gyro is 1, right controller gyro is 2. i.e. --gyro-remap 1 1 maps the left controller gyro to the left joystick, --gyro-remap 2 1 maps the right controller gyro to the left joystick,etc. Mapping 0: Disabled, 1: left joystick, 2: right joystick')

    parser.add_argument('--button-remap', nargs=3, metavar=('CONTROLLER', 'BUTTON', 'ACTION'),
                        help='Remap a button: controller ("left" or "right"), button code, action code')

    parser.add_argument('--vibration-level', nargs=2, metavar=('CONTROLLER', 'LEVEL'),
                        help='Set vibration level: controller ("left" or "right"), level (byte)')

    parser.add_argument('--fps-remap', nargs=4, metavar=('CONTROLLER', 'PROFILE', 'BUTTON', 'ACTION'),
                        help='FPS remapping: controller ("left" or "right"), profile (byte), button (byte), action (byte)')

    parser.add_argument('--sleep-time', nargs=2, metavar=('CONTROLLER', 'TIME'),
                        help='Set the sleep time of the controller: controller ("left" or "right"), time in minutes')

    # Argument for setting deadzone
    parser.add_argument('--deadzone', nargs=2, metavar=('CONTROLLER', 'LEVEL'),
                        help='Set deadzone level: controller ("left" or "right"), level (byte), default is 4. This is percentage of the stick. i.e. --deadzone left 4 sets the deadzone of the left controller to 4%')

    # Argument for setting sensitivity curve
    parser.add_argument('--curve', nargs=5, metavar=('CONTROLLER', 'TX', 'TY', 'BX', 'BY'),
                        help='Set sensitivity curve: controller ("left" or "right"), top x, top y, bottom x, bottom y. i.e. --curve left 0 0 0 0 sets the sensitivity curve of the left controller to the default curve. The default curve is a straight line. Lenovo allows for only two points for the curve, the curve is interpolated between the two points. Check repo for example picture using --curve right 85 85 5 30')

    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    
    # Process touchpad vibration argument
    if args.touchpad_vibration is not None:
        touch_vib_command = create_touchpad_vibration_command(args.touchpad_vibration)
        send_command(touch_vib_command)

    # Process RGB control argument
    if args.rgb_control:
        controller_arg, mode, color, brightness, speed, profile = args.rgb_control
        controller = controller_mapping(controller_arg)
        rgb_command = create_rgb_control_command(controller, int(mode), bytes.fromhex(color), int(brightness), int(speed), int(profile))
        send_command(rgb_command)
    # Process gyro remap argument
    if args.gyro_remap:
        gyro, joystick = args.gyro_remap
        gyro_remap_command = create_gyro_remap_command(int(gyro), int(joystick))
        send_command(gyro_remap_command)

    if args.button_remap:
        controller_arg, button, action = args.button_remap
        controller = controller_mapping(controller_arg)
        button_remap_command = create_button_remap_command(controller, int(button), int(action))
        send_command(button_remap_command)

    if args.vibration_level:
        controller_arg, level = args.vibration_level
        controller = controller_mapping(controller_arg)
        vibration_command = create_vibration_command(controller, int(level))
        send_command(vibration_command)

    if args.fps_remap:
        controller_arg, profile, button, action = args.fps_remap
        controller = controller_mapping(controller_arg)
        fps_remap_command = create_fps_remap_command(controller, int(profile), int(button), int(action))
        send_command(fps_remap_command)

    # Process sleep time argument
    if args.sleep_time:
        controller_arg, time_in_minutes = args.sleep_time
        controller = controller_mapping(controller_arg)
        sleep_time_command = create_sleep_time_command(controller, int(time_in_minutes))
        send_command(sleep_time_command)
    
    if args.deadzone:
        controller_arg, level = args.deadzone
        controller = controller_mapping(controller_arg)
        deadzone_command = create_deadzone_command(controller, int(level))
        send_command(deadzone_command)

    if args.curve:
        controller_arg, tx, ty, bx, by = args.curve
        controller = controller_mapping(controller_arg)
        curve_command = create_sensitivity_command(controller, int(tx), int(ty), int(bx), int(by))
        send_command(curve_command)
if __name__ == '__main__':
    main()

