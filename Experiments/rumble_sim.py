from evdev import InputDevice, ecodes, ff
import threading
import time

# Global flag to control the vibration thread
vibration_active = False

def create_rumble_effect(device, strong_magnitude, weak_magnitude, duration, delay):
    rumble = ff.Rumble(strong_magnitude=strong_magnitude, weak_magnitude=weak_magnitude)
    effect = ff.Effect(
        ecodes.FF_RUMBLE, -1, 0,
        ff.Trigger(0, delay),
        ff.Replay(duration, delay),
        ff.EffectType(ff_rumble_effect=rumble)
    )
    return device.upload_effect(effect)

def play_effect(device, effect_id):
    global vibration_active
    vibration_active = True

    device.write(ecodes.EV_FF, effect_id, 1)
    while vibration_active:
        time.sleep(0.1)

    device.erase_effect(effect_id)

def stop_vibration():
    global vibration_active
    vibration_active = False

def pulse_effect(device, strong_magnitude, weak_magnitude, duration, delay, interval, count):
    global vibration_active
    vibration_active = True

    for _ in range(count):
        if not vibration_active:
            break
        effect_id = create_rumble_effect(device, strong_magnitude, weak_magnitude, duration, delay)
        device.write(ecodes.EV_FF, effect_id, 1)
        time.sleep(duration/1000)
        device.erase_effect(effect_id)
        time.sleep(interval)

def explosion_shockwave(device, duration=1500):
    initial_strength = 0xffff
    effect_id = create_rumble_effect(device, initial_strength, initial_strength, 300, 0)
    play_effect(device, effect_id)
    time.sleep(0.3)
    for _ in range(5):
        strength = initial_strength // 2
        effect_id = create_rumble_effect(device, strength, strength, 200, 0)
        play_effect(device, effect_id)
        initial_strength = strength

def raindrops_effect(device, count=20):
    strength = 0x2000
    duration = 50
    interval = 0.2
    for _ in range(count):
        effect_id = create_rumble_effect(device, strength, strength, duration, 0)
        play_effect(device, effect_id)
        time.sleep(interval)
def test_vibration_strength(device, step=1000, duration=1000):
    """
    Iterates over the vibration strength range in steps, plays each level,
    and waits for user input to proceed to the next level.

    :param device: The device to play the vibration effect.
    :param step: The increment step for the vibration strength.
    :param duration: The duration of each vibration in milliseconds.
    """
    for strength in range(0, 65536, step):
        print(f"Testing vibration strength: {strength}")
        effect_id = create_rumble_effect(device, strength, strength, duration, 0)
        
        # Directly play and stop the effect
        device.write(ecodes.EV_FF, effect_id, 1)
        time.sleep(duration / 1000)  # Wait for the duration of the effect
        device.erase_effect(effect_id)

        user_input = input("Press Enter to test the next strength level or 'q' to quit: ")
        if user_input.lower() == 'q':
            break

        if strength == 65535:
            print("Test completed. This was the maximum strength.")


def heartbeat_simulation(device, count=10):
    strong = 0x8000
    weak = 0x8000
    duration = 200
    delay = 0
    interval = 0.5  # One second between heartbeats
    pulse_effect(device, strong, weak, duration, delay, interval, count)

def strong_muddy_vibration(device, duration=2000):
    strength = 0xffff
    interval = 0.5  # Interval of intensity change
    for _ in range(duration // int(interval * 1000)):
        effect_id = create_rumble_effect(device, strength, strength, 500, 0)
        device.write(ecodes.EV_FF, effect_id, 1)
        time.sleep(interval)
        strength = strength // 2 if strength > 0x2000 else 0xffff
        device.erase_effect(effect_id)

def quick_jolt(device, strength=0xffff):
    duration = .100  # Short duration for a sharp effect
    effect_id = create_rumble_effect(device, strength, strength, duration, 0)
    play_effect(device, effect_id)

def main():
    # device_path = input("Enter the device path (e.g., /dev/input/eventX): ")
    device_path = "/dev/input/event14"
    device = InputDevice(device_path)

    while True:
        print("\nRumble Effect Menu")
        print("1. Continuous Weak Rumble")
        print("2. Continuous Strong Rumble")
        print("3. Custom Rumble")
        print("4. Pulsating Rumble")
        print("5. Explosion Shockwave")
        print("6. Raindrops")
        print("7. Heartbeat")
        print("8. Strong Muddy Vibration")
        print("9. Quick Jolt")
        print("10. Test Vibration Strength")
        print("11. Exit")

        choice = input("Enter your choice: ")

        if choice in ['1', '2', '3', '4']:
            if choice == '1':
                effect_id = create_rumble_effect(device, 0x0000, 0xffff, 1000, 0)
            elif choice == '2':
                effect_id = create_rumble_effect(device, 0xffff, 0x0000, 1000, 0)
            elif choice == '3':
                strong = int(input("Enter strong magnitude (0 to 65535): "))
                weak = int(input("Enter weak magnitude (0 to 65535): "))
                duration = int(input("Enter duration in ms: "))
                delay = int(input("Enter delay in ms: "))
                effect_id = create_rumble_effect(device, strong, weak, duration, delay)
            elif choice == '4':
                strong = 0xffff
                weak = 0xffff
                duration = 500  # Short duration for pulse
                delay = 0
                interval = float(input("Enter pulse interval in seconds: "))
                count = int(input("Enter number of pulses: "))
                vibration_thread = threading.Thread(target=pulse_effect, args=(device, strong, weak, duration, delay, interval, count))
                vibration_thread.start()
                input("Press Enter to stop the vibration...")
                stop_vibration()
                vibration_thread.join()
                continue

            vibration_thread = threading.Thread(target=play_effect, args=(device, effect_id))
            vibration_thread.start()
            input("Press Enter to stop the vibration...")
            stop_vibration()
            vibration_thread.join()

        elif choice == '5':
            vibration_thread = threading.Thread(target=explosion_shockwave, args=(device,))
            vibration_thread.start()

        elif choice == '6':
            vibration_thread = threading.Thread(target=raindrops_effect, args=(device,))
            vibration_thread.start()

        elif choice == '7':
            vibration_thread = threading.Thread(target=heartbeat_simulation, args=(device,))
            vibration_thread.start()

        elif choice == '8':
            vibration_thread = threading.Thread(target=strong_muddy_vibration, args=(device,))
            vibration_thread.start()

        elif choice == '9':
            strength = int(input("Enter strength (0 to 65535): "))
            quick_jolt(device, strength)
        elif choice == '10':
            test_vibration_strength(device)
        elif choice == '11':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

        if choice in ['5', '6', '7', '8']:
            input("Press Enter to stop the vibration...")
            stop_vibration()
            vibration_thread.join()

    device.close()

if __name__ == "__main__":
    main()
