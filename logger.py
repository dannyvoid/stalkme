import os
import csv
import math
import time
import threading
from pathlib import Path
from pynput import mouse, keyboard

monitor_count = 2
monitor_width_px = 1920
monitor_height_px = 1080
monitor_diagonal_in = 27
monitor_diagonal_px = math.sqrt(monitor_width_px**2 + monitor_height_px**2)
dpi = monitor_diagonal_px / monitor_diagonal_in

# sqlite or mongodb would probably be better
# but this is the most performant option without a rewrite of the sanic server
log_file = Path(__file__).parent / "persistent" / "log.csv"

prev_position = None
total_distance_in = 0

log_queue = []
lock = threading.Lock()

log_interval = 3


def initialize_log_file(log_file_path: Path) -> None:
    global total_distance_in

    log_file_path = Path(log_file_path)
    if not log_file_path.exists() or log_file_path.stat().st_size == 0:

        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["timestamp", "event", "button", "position", "distance_in_inches"]
            )
    else:
        with open(log_file, "r", newline="") as f:
            reader = csv.reader(f)
            last_mouse_move = next(
                (line for line in reversed(list(reader)) if line[1] == "Moved"), None
            )
            if last_mouse_move:
                total_distance_in = (
                    float(last_mouse_move[-1]) if last_mouse_move[-1] else 0.0
                )
            else:
                total_distance_in = 0.0


def log_event(event, button=None, position=None, distance_in_inches=None) -> None:
    timestamp = time.time()
    with lock:
        log_queue.append([timestamp, event, button, position, distance_in_inches])


def calculate_distance(x1, y1, x2, y2) -> float:
    distance_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    distance_in = distance_px / dpi
    return distance_in


def on_move(x, y) -> None:
    global prev_position, total_distance_in
    if prev_position is not None:
        distance_in = calculate_distance(prev_position[0], prev_position[1], x, y)
        log_event("Moved", position=(x, y), distance_in_inches=distance_in)
    prev_position = (x, y)


def on_click(x, y, button, pressed) -> None:
    event = "Pressed" if pressed else "Released"
    log_event(event, button=button, position=(x, y))


def on_press(key) -> None:
    log_event("Key Pressed")


def on_release(key) -> None:
    log_event("Key Released")


def print_options() -> None:
    print("Configuration:")
    print(f"Log file: {log_file}")
    print(f"Log file exists: {log_file.exists()}")
    print(f"Log interval: {log_interval} seconds")
    print(f"Monitor count: {monitor_count}")
    print(f"Monitor width: {monitor_width_px}")
    print(f"Monitor height: {monitor_height_px}")
    print(f"Monitor diagonal: {monitor_diagonal_in} inches")
    print(f"Monitor diagonal: {monitor_diagonal_px} pixels")
    print(f"Monitor DPI: {dpi}")
    print()


def flush_log_queue(interval: int) -> None:
    global log_queue
    while True:
        if log_queue:
            with lock:
                events_to_write = log_queue[:]
                log_queue.clear()

            with open(log_file, "a", newline="") as f:
                writer = csv.writer(f)
                for event in events_to_write:
                    writer.writerow(event)
                    print(event)

        if interval > 0:
            time.sleep(interval)
        else:
            break


def main() -> None:
    print_options()

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
