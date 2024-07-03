import csv
import math
import time
import threading
from pathlib import Path
from pynput import mouse, keyboard

monitor_width_px = 1920
monitor_height_px = 1080
monitor_diagonal_px = math.sqrt(monitor_width_px**2 + monitor_height_px**2)
monitor_diagonal_in = 27
dpi = monitor_diagonal_px / monitor_diagonal_in

log_file = Path(__file__).parent / "persistent" / "log.csv"

prev_position = None
prev_timestamp = 0
debounce_threshold = 0.001  # seconds

log_queue = []
lock = threading.Lock()

log_interval = 3


def initialize_log_file(log_file_path: Path) -> None:
    log_file_path = Path(log_file_path)
    if not log_file_path.exists() or log_file_path.stat().st_size == 0:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["timestamp", "event", "button", "position", "distance_in_inches"]
            )


def log_event(event, button=None, position=None, distance_in_inches=None) -> None:
    print_event_data = False
    timestamp = time.time()
    event_data = [timestamp, event, button, position, distance_in_inches]

    if print_event_data:
        print(event_data)

    with lock:
        log_queue.append(event_data)


def calculate_distance(x1, y1, x2, y2) -> float:
    print_calculation = False
    distance_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    distance_in = distance_px / dpi

    if print_calculation:
        print(
            f"calculate_distance: ({x1}, {y1}) -> ({x2}, {y2}) = {distance_px} px, {distance_in} in"
        )
    return distance_in


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


def flush_log_queue(interval: int) -> None:
    global log_queue
    print_event = False
    while True:
        if log_queue:
            with lock:
                events_to_write = log_queue[:]
                log_queue.clear()
            with open(log_file, "a", newline="") as f:
                writer = csv.writer(f)
                for event in events_to_write:
                    writer.writerow(event)
                    if print_event:
                        print(event)
                print(f"Events written: {len(events_to_write)}")
        if interval > 0:
            time.sleep(interval)
        else:
            break


def main() -> None:
    print_config()

    initialize_log_file(log_file)

    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    flush_thread = threading.Thread(target=flush_log_queue, args=(log_interval,))
    flush_thread.daemon = True
    flush_thread.start()

    mouse_listener.start()
    keyboard_listener.start()

    mouse_listener.join()
    keyboard_listener.join()


if __name__ == "__main__":
    main()
