import sqlite3
import math
import time
import threading
from pathlib import Path
from pynput import mouse, keyboard
from inputs import get_gamepad, UnpluggedError

monitor_width_px = 1920
monitor_height_px = 1080
monitor_diagonal_px = math.sqrt(monitor_width_px**2 + monitor_height_px**2)
monitor_diagonal_in = 27
dpi = monitor_diagonal_px / monitor_diagonal_in

log_file = Path(__file__).parent / "persistent" / "log.db"

prev_position = None
prev_timestamp = 0

debounce_threshold = 0.001  # seconds

log_queue = []
lock = threading.Lock()

log_interval = 60


def initialize_db(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            event TEXT,
            button TEXT,
            position TEXT,
            distance_in_inches REAL
        )
    """
    )
    conn.commit()
    conn.close()


def log_event(event_type, button=None, position=None, distance_in_inches=None):
    timestamp = time.time()

    # Convert button to string if it's not None
    if button is not None:
        button = str(button)

    # Convert position tuple to a string or None if position is None
    if position:
        position_str = f"({position[0]}, {position[1]})"
    else:
        position_str = None

    event_data = (timestamp, event_type, button, position_str, distance_in_inches)

    with lock:
        log_queue.append(event_data)


def calculate_distance(x1, y1, x2, y2) -> float:
    distance_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    distance_in = distance_px / dpi
    return distance_in


def flush_log_queue(interval):
    conn = sqlite3.connect(log_file)
    c = conn.cursor()

    while True:
        if log_queue:
            with lock:
                events_to_write = log_queue[:]
                log_queue.clear()

            for event in events_to_write:
                timestamp, event_type, button, position, distance_in_inches = event
                c.execute(
                    """
                    INSERT INTO events (timestamp, event, button, position, distance_in_inches)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (timestamp, event_type, button, position, distance_in_inches),
                )

            conn.commit()
            print(f"Events written: {len(events_to_write)}")

        if interval > 0:
            time.sleep(interval)
        else:
            break

    conn.close()


def on_move(x, y) -> None:
    global prev_position, prev_timestamp
    current_timestamp = time.time()
    if (
        prev_position is not None
        and (current_timestamp - prev_timestamp) > debounce_threshold
    ):
        distance_in = calculate_distance(prev_position[0], prev_position[1], x, y)
        log_event("Moved", position=(x, y), distance_in_inches=distance_in)
        prev_timestamp = current_timestamp
    prev_position = (x, y)


def on_click(x, y, button, pressed) -> None:
    event = "Pressed" if pressed else "Released"
    log_event(event, button=button, position=(x, y))


def on_press(key) -> None:
    log_event("Key Pressed")


def on_release(key) -> None:
    log_event("Key Released")


def handle_gamepad_events() -> None:

    # Track the state of the triggers
    trigger_states = {"ABS_Z": False, "ABS_RZ": False}

    # Track the state of the joysticks
    joystick_states = {
        "ABS_X": False,
        "ABS_Y": False,
        "ABS_RX": False,
        "ABS_RY": False,
    }

    # Define deadzone thresholds for joysticks
    joystick_deadzone = {
        "ABS_X": 255 * 0.2,
        "ABS_Y": 32768 * 0.15,
        "ABS_RX": 255 * 0.2,
        "ABS_RY": 32768 * 0.15,
    }

    trigger_threshold = 255 * 0.45  # 45% of the range

    while True:
        try:
            events = get_gamepad()
            for event in events:
                if event.ev_type == "Key" or event.ev_type == "Absolute":
                    if event.ev_type == "Key" and event.state == 1:
                        log_event("Gamepad Pressed")
                    elif event.ev_type == "Key" and event.state == 0:
                        log_event("Gamepad Released")
                    elif event.ev_type == "Absolute":
                        if event.code in ["ABS_HAT0X", "ABS_HAT0Y"]:
                            if event.state != 0:
                                log_event("Gamepad Pressed")
                            else:
                                log_event("Gamepad Released")
                        elif event.code in ["ABS_Z", "ABS_RZ"]:  # Trigger inputs
                            if (
                                event.state >= trigger_threshold
                                and not trigger_states[event.code]
                            ):
                                log_event("Gamepad Pressed")
                                trigger_states[event.code] = True
                            elif (
                                event.state < trigger_threshold
                                and trigger_states[event.code]
                            ):
                                log_event("Gamepad Released")
                                trigger_states[event.code] = False
                        elif event.code in [
                            "ABS_X",
                            "ABS_Y",
                            "ABS_RX",
                            "ABS_RY",
                        ]:  # Joystick inputs
                            deadzone = joystick_deadzone.get(event.code, 255 * 0.15)
                            if (
                                abs(event.state) >= deadzone
                                and not joystick_states[event.code]
                            ):
                                log_event("Gamepad Pressed")
                                joystick_states[event.code] = True
                            elif (
                                abs(event.state) < deadzone
                                and joystick_states[event.code]
                            ):
                                log_event("Gamepad Released")
                                joystick_states[event.code] = False
            time.sleep(0.001)
        except UnpluggedError:
            time.sleep(1)


def print_config() -> None:
    print("Configuration:")
    print(f"Log file: {log_file}")
    print(f"Log file exists: {log_file.exists()}")
    print(f"Log interval: {log_interval} seconds")
    print(f"Monitor width: {monitor_width_px}")
    print(f"Monitor height: {monitor_height_px}")
    print(f"Monitor diagonal: {monitor_diagonal_in} inches")
    print(f"Monitor diagonal: {monitor_diagonal_px} pixels")
    print(f"Monitor DPI: {dpi}")
    print()


def main() -> None:
    print_config()

    initialize_db(log_file)

    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    flush_thread = threading.Thread(target=flush_log_queue, args=(log_interval,))
    flush_thread.daemon = True
    flush_thread.start()

    gamepad_thread = threading.Thread(target=handle_gamepad_events)
    gamepad_thread.daemon = True
    gamepad_thread.start()

    mouse_listener.start()
    keyboard_listener.start()

    mouse_listener.join()
    keyboard_listener.join()
    gamepad_thread.join()


if __name__ == "__main__":
    main()
