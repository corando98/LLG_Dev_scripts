import os
import subprocess
import logging
import sys
import time

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def execute_acpi_command(command):
    """
    Executes an ACPI command and returns the output.
    Uses subprocess for robust command execution.

    Args:
        command (str): The ACPI command to be executed.
    
    Returns:
        str: The output from the ACPI command execution.
    """
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {e.stderr}")
        return None
    
def parse_fan_curve(raw_data):
    """
    Parses the raw fan curve data and formats it into a readable string.
    The data is expected in a specific format with hex values representing the fan speeds and temperatures.
    """
    try:
        logging.info("Starting to parse fan curve data.")

        # Find the start and end of the hex data block
        hex_data_start = raw_data.find('{')
        hex_data_end = raw_data.find('}') + 1
        if hex_data_start == -1 or hex_data_end == -1:
            raise ValueError("Invalid data format")

        logging.info(f"Extracted hex data block: {raw_data[hex_data_start:hex_data_end]}")

        # Extract and clean up the hex data
        hex_data = raw_data[hex_data_start:hex_data_end].strip('{}').split(', ')
        data_values = []
        for i in range(0, len(hex_data), 4):  # Process every 4 bytes
            hex_group = ''.join(hex_data[i:i+4]).replace('0x', '').replace(' ', '')
            # Reverse the order of bytes for little endian format
            hex_group = ''.join(reversed([hex_group[j:j+2] for j in range(0, len(hex_group), 2)]))
            logging.info(f"Hex group to convert: {hex_group}")
            int_value = int(hex_group, 16)
            data_values.append(int_value)

        logging.info(f"Parsed data values: {data_values}")

        # Extracting fan speeds and temperatures
        speeds_length = data_values[0]
        fan_speeds = data_values[1:speeds_length + 1]
        temps_length = data_values[speeds_length + 1]
        temperatures = data_values[speeds_length + 2: speeds_length + 2 + temps_length]

        logging.info(f"Fan speeds: {fan_speeds}")
        logging.info(f"Temperatures: {temperatures}")

        # Format the output
        formatted_output = "Fan Curve:\n"
        for i in range(min(len(fan_speeds), len(temperatures))):
            formatted_output += f"Temperature {temperatures[i]}°C: Fan Speed {fan_speeds[i]}%\n"

        return formatted_output

    except Exception as e:
        logging.error(f"Error parsing fan curve: {e}")
        return "Failed to parse fan curve."

def retrieve_fan_curve():
    """
    Retrieves the fan curve from the ACPI interface and returns the parsed output.
    """
    command = "echo '\\_SB.GZFD.WMAB 0 0x05 0x0000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    raw_data = execute_acpi_command(command)
    return parse_fan_curve(raw_data)

#echo '\_SB.GZFD.WMAE 0 0x11 0x04020000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call
def get_full_fan_speed():
    """
    Full fan speed is the maximum fan speed that can be set.

    Returns:
        str: ?
    """
    command = "echo '\\_SB.GZFD.WMAE 0 0x11 0x04020000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)
    # Assuming the output is a hexadecimal value
    first_newline_position = output.find('\n')
    output = output[first_newline_position+1:first_newline_position+6]
    try:
        fan_speed = output  # Convert from hex to decimal
        return fan_speed
    except ValueError:
        logging.error("Failed to parse fan speed.")
        return "N/A"
# FFSS Full speed mode set on /off
# echo '\_SB.GZFD.WMAE 0 0x12 0x0104020000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call
# echo '\_SB.GZFD.WMAE 0 0x12 0x0004020000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call
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

def set_fan_curve(fan_table):
    """
    Sets a new fan curve based on the provided fan table array.
    The fan table should contain fan speed values that correspond to different temperature thresholds.

    Args:
        fan_table (list): An array of fan speeds to set the fan curve.

    Returns:
        str: The output from setting the new fan curve.
    """
    # Assuming Fan ID and Sensor ID are both 0 (as they are ignored)
    fan_id_sensor_id = '0x00, 0x00'

    # Assuming the temperature array length and values are ignored but required
    temp_array_length = '0x0A, 0x00, 0x00, 0x00'  # Length 10 in hex
    temp_values = ', '.join([f'0x{temp:02x}, 0x00' for temp in range(0, 101, 10)]) + ', 0x00'

    # Fan speed values in uint16 format with null termination
    fan_speed_values = ', '.join([f'0x{speed:02x}, 0x00' for speed in fan_table]) + ', 0x00'

    # Constructing the full command
    command = f"echo '\\_SB.GZFD.WMAB 0 0x06 {{{fan_id_sensor_id}, {temp_array_length}, {fan_speed_values}, {temp_array_length}, {temp_values}}}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)



def set_tdp_value(mode, wattage):
    """
    Sets the Thermal Design Power (TDP) value for the specified mode.
    This function controls the power usage and heat generation of the CPU.

    Args:
        mode (str): The TDP mode ('Slow', 'Steady', 'Fast').
        wattage (int): The desired TDP wattage.

    Returns:
        str: The output from setting the TDP value.
    """
    mode_mappings = {'Slow': '0x01', 'Steady': '0x02', 'Fast': '0x03'}
    mode_code = mode_mappings.get(mode, '0x02')  # Default to 'Steady' if mode is not found

    # Create the command with the desired format
    command = f"echo '\\_SB.GZFD.WMAE 0 0x12 {{0x00, 0xFF, {mode_code}, 0x01, {wattage}, 0x00, 0x00, 0x00}}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"

    # Logging the command
    logging.info(f"Command to set TDP value: {command}")

    output = execute_acpi_command(command)

    # Logging the output
    logging.info(f"Output from setting TDP value: {output}")

    return output

def set_overclocking_status(enable):
    """
    Enable or disable overclocking.

    Args:
        enable (bool): True to enable, False to disable.

    Returns:
        str: The result of the overclocking operation.
    """
    status = '0x01' if enable else '0x00'
    command = f"echo '\\_SB.GZFD.WMAE 0 0x33 {status}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)

def get_gpu_overclocking_status():
    """
    Get the GPU overclocking status.

    Returns:
        str: GPU overclocking status.
    """
    command = "echo '\\_SB.GZFD.WMAE 0 0x04' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)

def set_thermal_mode(mode_id):
    """
    Set the thermal mode of the system.

    Args:
        mode_id (int): The ID of the thermal mode to set.

    Returns:
        str: The result of the operation.
    """
    command = f"echo '\\_SB.GZFD.WMAA 0 0x03 {mode_id}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)

def get_current_thermal_mode():
    """
    Get the current thermal mode of the system.

    Returns:
        str: The current thermal mode.
    """
    command = "echo '\\_SB.GZFD.WMAA 0 0x02' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)

def set_smart_fan_mode(mode_value):
    """
    Set the Smart Fan Mode of the system.

    The Smart Fan Mode controls the system's cooling behavior. Different modes can be set to 
    optimize the balance between cooling performance and noise level.

    Args:
        mode_value (int): The value of the Smart Fan Mode to set.
                          Known values:
                          - 0: Quiet Mode - Lower fan speed for quieter operation.
                          - 1: Balanced Mode - Moderate fan speed for everyday usage.
                          - 2: Performance Mode - Higher fan speed for intensive tasks.
                          - 224: Extreme Mode
                          - 255: Custom Mode - Custom fan curve can be set?.

    Returns:
        str: The result of the operation. Returns None if an error occurs.
    """
    command = f"echo '\\_SB.GZFD.WMAA 0 0x2C {mode_value}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)


def get_smart_fan_mode():
    """
    Get the current Smart Fan Mode of the system.

    This function retrieves the current setting of the Smart Fan mode as specified in the WMI documentation.

    Returns:
        str: The current Smart Fan Mode. The return value corresponds to:
             - '0': Quiet Mode
             - '1': Balanced Mode
             - '2': Performance Mode
             - '224': Extreme Mode
             - '255': Custom Mode
             Returns None if an error occurs.
    """
    command = "echo '\\_SB.GZFD.WMAA 0 0x2D' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)
    first_newline_position = output.find('\n')
    output = output[first_newline_position+1:first_newline_position+5]
    return output


def get_smart_fan_setting_mode():
    """
    Get the current Smart Fan Setting Mode of the system.

    This function retrieves the specific setting or configuration of the Smart Fan.

    Returns:
        str: The current Smart Fan Setting Mode. The return value might require interpretation based on the system's BIOS.
             Known values might include various numeric codes representing specific fan curves or settings.
             Returns None if an error occurs.
    """
    command = "echo '\\_SB.GZFD.WMAA 0 0x2E' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)
    first_newline_position = output.find('\n')
    output = output[first_newline_position+1:first_newline_position+5]
    return output


def get_fan_speed():
    """
    Get the current fan speed in %.

    Returns:
        str: The current fan speed in %.
    """
    command = "echo '\\_SB.GZFD.WMAE 0 0x11 0x04030001' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)

    # Assuming the output is a hexadecimal value
    first_brace_position = output.find('{')
    output = output[first_brace_position+1:first_brace_position+5]
    try:
        fan_speed = int(output, 16)  # Convert from hex to decimal
        return fan_speed
    except ValueError:
        logging.error("Failed to parse fan speed.")
        return "N/A"
    
def get_cpu_temperature():
    """
    Get the current CPU temperature.

    Returns:
        str: The current CPU temperature.
    """
    command = "echo '\\_SB.GZFD.WMAE 0 0x11 0x05040000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)
    first_newline_position = output.find('\n')
    output = output[first_newline_position+1:first_newline_position+5]
    try:
        return int(output, 16) # Convert from hex to decimal
    except ValueError:
        logging.error("Failed to parse CPU temperature.")
        return "N/A"
def get_gpu_temperature():
    """
    Get the current GPU temperature.

    Returns:
        str: The current GPU temperature.
    """
    command = "echo '\\_SB.GZFD.WMAE 0 0x11 0x05050000' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)
    first_newline_position = output.find('\n')
    output = output[first_newline_position+1:first_newline_position+5]
    try:
        return int(output, 16) # Convert from hex to decimal
    except ValueError:
        logging.error("Failed to parse GPU temperature.")
        return "N/A"

def get_tdp_value(mode):
    """
    Retrieves the Thermal Design Power (TDP) value for the specified mode.

    Args:
        mode (str): The TDP mode ('Slow', 'Steady', 'Fast').

    Returns:
        str: The output from retrieving the TDP value, or None if an error occurs.
    """
    mode_mappings = {'Slow': '01', 'Steady': '02', 'Fast': '03'}
    mode_code = mode_mappings.get(mode, '02')  # Default to 'Steady' if mode is not found

    # Using the format without braces for simplicity
    command = f"echo '\\_SB.GZFD.WMAE 0 0x11 0x01{mode_code}FF00' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    response = execute_acpi_command(command)


    if response:
        # Parse the response to extract the TDP value
        # Implement the parsing logic based on the response format
        return response
    else:
        logging.error("Failed to retrieve TDP value.")
        return None

def get_all_tdp_values():
    """
    Retrieves the Thermal Design Power (TDP) values for all modes.

    Returns:
        str: A formatted string containing the TDP values for all modes.
    """
    mode_mappings = {'Slow': '01', 'Steady': '02', 'Fast': '03'}
    tdp_values = []

    for mode, code in mode_mappings.items():
        command = f"echo '\\_SB.GZFD.WMAE 0 0x11 0x01{code}FF00' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
        response = execute_acpi_command(command)
        first_newline_position = response.find('\n')
        response = response[first_newline_position+1:first_newline_position+5]
        response = int(response, 16) # Convert from hex to decimal

        if response:
            # Add parsing logic here if necessary
            tdp_values.append(f"{mode} mode: {response}")
        else:
            tdp_values.append(f"{mode} mode: Failed to retrieve value")

    return '\n'.join(tdp_values)



def set_lighting_status(lighting_id, state_type, brightness_level):
    """
    Sets the lighting status of a specific component identified by the lighting ID.
    This can control the brightness and state (on/off) of the component's lighting.

    Args:
        lighting_id (int): The ID of the lighting component.
        state_type (int): The state type (e.g., on/off).
        brightness_level (int): The brightness level.

        power button = 0x03
        left stick = 0x01?
        right stick = 0x02?

    Returns:
        str: The output from setting the lighting status.
    """
    command = f"echo '\\_SB.GZFD.WMAF 0 0x02 {{{lighting_id}, {state_type}, {brightness_level}}}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    return execute_acpi_command(command)

def get_lighting_status(lighting_id):
    """
    Retrieves the current lighting status for a specific component identified by the lighting ID.

    Args:
        lighting_id (int): The ID of the lighting component to check.

    Returns:
        str: The current lighting status of the specified component.
    """
    command = f"echo '\\_SB.GZFD.WMAF 0 0x01 {lighting_id}' | sudo tee /proc/acpi/call; sudo cat /proc/acpi/call"
    output = execute_acpi_command(command)
    first_newline_position = output.find('\n')
    output = output[first_newline_position+1:first_newline_position+15]
    return output

def input_fan_curve():
    """
    Collects user input to define a new fan curve with temperature thresholds in increments of 10 degrees up to 100.
    Returns:
        list: List of fan speeds corresponding to temperature thresholds.
    """
    fan_curve = []
    for temp in range(0, 101, 10):
        speed = int(input(f"Enter fan speed for temperature {temp}°C: "))
        fan_curve.append(speed)
    return fan_curve

def input_tdp_settings():
    """
    Collects user input for TDP settings.
    Returns:
        tuple: (mode, wattage) for TDP settings.
    """
    mode = input("Enter TDP mode (Slow/Steady/Fast): ")
    wattage = int(input("Enter desired TDP wattage: "))
    return mode, wattage

def input_lighting_settings():
    """
    Collects user input for lighting settings.
    Returns:
        tuple: (lighting_id, state_type, brightness_level) for lighting settings.
    """
    lighting_id = int(input("Enter Lighting ID: "))
    state_type = int(input("Enter State Type (0 for off, 1 for on): "))
    brightness_level = int(input("Enter Brightness Level (0-100): "))
    return lighting_id, state_type, brightness_level

def input_lighting_id():
    """
    Collects user input for lighting ID.
    Returns:
        int: The lighting ID.
    """
    return int(input("Enter Lighting ID: "))

def continuously_update_status():
    """
    Continuously update and display system status information every second.
    """
    try:
        while True:
            fan_speed = get_fan_speed()
            cpu_temp = get_cpu_temperature()
            # gpu_temp = get_gpu_temperature()
            smart_fan_mode = get_smart_fan_mode()
            lighting_status = get_lighting_status(3)
            tdp_values = get_all_tdp_values()
            # Clear the screen for better readability
            os.system('cls' if os.name == 'nt' else 'clear')

            print(f"Fan Speed: {fan_speed} %")
            print(f"CPU Temperature: {cpu_temp}°C")
            # print(f"GPU Temperature: {gpu_temp}°C")
            print(f"Smart Fan Mode: {smart_fan_mode}")
            print(f"Power Button Lighting Status: {lighting_status}")
            print(f"TDP Values for custom mode:\n{tdp_values}")

            # Wait for 1 second before updating the values again
            time.sleep(1)
    except KeyboardInterrupt:
        print("Status update stopped.")

#Dock mode, enables fan full speed, enabled custom mode, and sets steady, slow, and fast TDP to 35W
def dock_mode():
    """
    Sets the system to dock mode.
    """
    set_full_fan_speed(True)
    set_smart_fan_mode(255)
    set_tdp_value('Slow', 35)
    set_tdp_value('Steady', 35)
    set_tdp_value('Fast', 35)
def undock_mode():
    """
    Sets the system to undock mode.
    """
    set_full_fan_speed(False)
    set_smart_fan_mode(2)
    set_tdp_value('Slow', 25)
    set_tdp_value('Steady', 25)
    set_tdp_value('Fast', 30)

def set_custom_tdp(slow, steady, fast):
    """
    Sets the system to custom TDP mode.
    """
    set_tdp_value('Slow', slow)
    set_tdp_value('Steady', steady)
    set_tdp_value('Fast', fast)

if __name__ == "__main__":
    logging.info("Starting Legion Go Control Script")

    # Simple CLI
    while True:
        print("\nOptions:")
        print("1. Retrieve Fan Curve")
        print("2. Set Fan Curve")
        print("3. Set TDP Value")
        print("4. Set Lighting Status")
        print("5. Get Lighting Status")
        print("6. Get TDP Status")
        print("7. Get Fan Speed")
        print("8. Get CPU Temperature")
        print("9. Get GPU Temperature")
        print("10. Set Thermal Mode")
        print("11. Get Current Thermal Mode")
        print("12. Set Smart Fan Mode")
        print("13. Get Smart Fan Mode")
        print("14. Get Smart Fan Setting Mode")
        print("15. Exit")
        print("16. Continuously Update System Status")
        print("17. Enable Overclocking")
        print("18. Disable Overclocking")
        print("19. Get GPU Overclocking Status")
        print("20. Set Smart Fan Mode to Custom")
        print("21. Set Smart Fan Mode to Extreme (Powersaving?)")
        print("22. Set Smart Fan Mode to Balanced")
        print("23. Set Smart Fan Mode to Quiet")
        print("24. Set Full Fan Speed Mode On")
        print("25. Set Full Fan Speed Mode Off")
        print("26. Get Full Fan Speed Mode Status")
        print("27. Set Dock Mode")
        print("28. Set Undock Mode")


        choice = input("Enter your choice: ")

        if choice == '1':
            result = retrieve_fan_curve()
            if result:
                logging.info(f"Current fan curve: {result}")
            else:
                logging.error("Failed to retrieve fan curve.")

        elif choice == '2':
            fan_curve = input_fan_curve()
            result = set_fan_curve(fan_curve)
            if result:
                logging.info(f"Fan curve set successfully: {result}")
            else:
                logging.error("Failed to set fan curve.")
        elif choice == '3':
            mode, wattage = input_tdp_settings()
            result = set_tdp_value(mode, wattage)
            if result:
                logging.info(f"TDP value set successfully: {result}")
            else:
                logging.error("Failed to set TDP value.")
        elif choice == '4':
            lighting_id, state_type, brightness_level = input_lighting_settings()
            result = set_lighting_status(lighting_id, state_type, brightness_level)
            if result:
                logging.info(f"Lighting status set successfully: {result}")
            else:
                logging.error("Failed to set lighting status.")
        elif choice == '5':
            lighting_id = input_lighting_id()
            result = get_lighting_status(lighting_id)
            if result:
                logging.info(f"Lighting status: {result}")
            else:
                logging.error("Failed to retrieve lighting status.")

        elif choice == '6':
            tdp_values = get_all_tdp_values()
            logging.info(f"TDP Values:\n{tdp_values}")
        

        elif choice == '7':
            fan_speed = get_fan_speed()
            logging.info(f"Fan Speed: {fan_speed}")

        elif choice == '8':
            cpu_temp = get_cpu_temperature()
            logging.info(f"CPU Temperature: {cpu_temp}")

        elif choice == '9':
            gpu_temp = get_gpu_temperature()
            logging.info(f"GPU Temperature: {gpu_temp}")

        elif choice == '10':
            mode_id = int(input("Enter Thermal Mode ID: "))
            result = set_thermal_mode(mode_id)
            if result:
                logging.info(f"Thermal mode set successfully: {result}")
            else:
                logging.error("Failed to set thermal mode.")

        elif choice == '11':
            current_mode = get_current_thermal_mode()
            logging.info(f"Current Thermal Mode: {current_mode}")

        elif choice == '12':
            mode_value = int(input("Enter Smart Fan Mode Value: "))
            result = set_smart_fan_mode(mode_value)
            if result:
                logging.info(f"Smart Fan Mode set successfully: {result}")
            else:
                logging.error("Failed to set Smart Fan Mode.")

        elif choice == '13':
            smart_fan_mode = get_smart_fan_mode()
            logging.info(f"Smart Fan Mode: {smart_fan_mode}")

        elif choice == '14':
            smart_fan_setting_mode = get_smart_fan_setting_mode()
            logging.info(f"Smart Fan Setting Mode: {smart_fan_setting_mode}")

        elif choice == '15':
            logging.info("Exiting script.")
            break
        elif choice == '16':
            continuously_update_status()
        elif choice == '17':
            set_overclocking_status(True)
        elif choice == '18':
            set_overclocking_status(False)
        elif choice == '19':
            logging.info(get_gpu_overclocking_status())
        elif choice == '20':
            logging.info(set_smart_fan_mode(255))
        elif choice == '21':
            logging.info(set_smart_fan_mode(224))
        elif choice == '22':
            logging.info(set_smart_fan_mode(2))
        elif choice == '23':
            logging.info(set_smart_fan_mode(1))
        elif choice == '24':
            logging.info(set_full_fan_speed(True))
        elif choice == '25':
            logging.info(set_full_fan_speed(False))
        elif choice == '26':
            logging.info(get_full_fan_speed())
        elif choice == '27':
            dock_mode()
        elif choice == '28':
            undock_mode()

        
        else:
            logging.warning("Invalid choice. Please try again.")

    logging.info("Script finished.")