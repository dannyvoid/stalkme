import os
import re
import datetime
import sqlite3
from pathlib import Path
from sanic import Sanic, response

app = Sanic(__name__)

log_file = Path(__file__).parent.parent / "persistent" / "log.db"

cached_data = None
cached_timestamp = None

debug = True


def get_current_datetime(datetime_format="%Y-%m-%d %I:%M:%S %p") -> str:
    try:
        return datetime.datetime.now().strftime(datetime_format)
    except ValueError:
        return datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")


def get_origin_datetime(log_file, manual_timestamp=None) -> str:
    if manual_timestamp:
        datetime_from_file = manual_timestamp
    else:
        datetime_from_file = datetime.datetime.fromtimestamp(
            os.path.getctime(log_file)
        ).strftime("%Y-%m-%d %I:%M:%S %p")

    return datetime_from_file


def fetch_db_data(time_delta=None) -> dict:
    global cached_data, cached_timestamp

    start_time = datetime.datetime.now()
    data = {
        "clicks_left": 0,
        "clicks_right": 0,
        "clicks_middle": 0,
        "gamepad_actions": 0,
        "mouse_movement": 0,
        "key_presses": 0,
        "__current_time__": get_current_datetime(),
        "__logging_since__": custom_timedelta_operation(time_delta),
        "__logging_size__": os.path.getsize(log_file) / 1024,
    }

    try:
        with sqlite3.connect(log_file) as conn:
            if time_delta:
                start_datetime = datetime.datetime.now() - time_delta
                data["clicks_left"] = count_clicks(
                    conn, "Pressed", "Button.left", start_datetime
                )
                data["clicks_right"] = count_clicks(
                    conn, "Pressed", "Button.right", start_datetime
                )
                data["clicks_middle"] = count_clicks(
                    conn, "Pressed", "Button.middle", start_datetime
                )
                data["key_presses"] = count_events(conn, "Key Pressed", start_datetime)
                data["gamepad_actions"] = count_events(
                    conn, "Gamepad Pressed", start_datetime
                )
                data["mouse_movement"] = calculate_mouse_movement(conn, start_datetime)

            else:
                data["clicks_left"] = count_clicks(conn, "Pressed", "Button.left")
                data["clicks_right"] = count_clicks(conn, "Pressed", "Button.right")
                data["clicks_middle"] = count_clicks(conn, "Pressed", "Button.middle")
                data["key_presses"] = count_events(conn, "Key Pressed")
                data["gamepad_actions"] = count_events(conn, "Gamepad Pressed")
                data["mouse_movement"] = calculate_mouse_movement(conn)

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    end_time = datetime.datetime.now()

    cached_data = data
    cached_timestamp = datetime.datetime.now()

    if debug:
        print(f"Data fetched in {end_time - start_time}")
        print(data)

    return data


def custom_timedelta_operation(timedelta_input):
    # Check if the input is already a string, if not, convert it to a string
    if isinstance(timedelta_input, datetime.timedelta):
        timedelta_str = str(timedelta_input)
    else:
        timedelta_str = timedelta_input

    # Regular expression pattern to match days (optional), hours, minutes, and seconds
    pattern = r"(?:(\d+) day(?:s)?, )?(\d+):(\d+):(\d+)"

    # Extract days, hours, minutes, and seconds from the string
    match = re.match(pattern, timedelta_str)
    if not match:
        raise ValueError("Invalid timedelta string format")

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2))
    minutes = int(match.group(3))
    seconds = int(match.group(4))

    # Create a timedelta object from the extracted components
    timedelta_obj = datetime.timedelta(
        days=days, hours=hours, minutes=minutes, seconds=seconds
    )

    # Get the current time
    current_time = datetime.datetime.now()

    # Subtract the timedelta from the current time
    result_time = current_time - timedelta_obj

    # Return the result as a formatted string
    return result_time.strftime("%Y-%m-%d %I:%M:%S %p")


def count_clicks(conn, event_type, button, start_datetime=None):
    cursor = conn.cursor()
    if start_datetime:
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event = ? AND button = ? AND timestamp >= ?",
            (event_type, button, start_datetime.timestamp()),
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event = ? AND button = ?",
            (event_type, button),
        )
    return cursor.fetchone()[0] if cursor else 0  # Handle case where cursor is None


def count_events(conn, event_type, start_datetime=None):
    cursor = conn.cursor()
    if start_datetime:
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event = ? AND timestamp >= ?",
            (event_type, start_datetime.timestamp()),
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event = ?",
            (event_type,),
        )
    return cursor.fetchone()[0] if cursor else 0  # Handle case where cursor is None


def calculate_mouse_movement(conn, start_datetime=None):
    cursor = conn.cursor()
    if start_datetime:
        cursor.execute(
            "SELECT SUM(distance_in_inches) FROM events WHERE timestamp >= ?",
            (start_datetime.timestamp(),),
        )
    else:
        cursor.execute(
            "SELECT SUM(distance_in_inches) FROM events",
        )
    total_mouse_movement = cursor.fetchone()[0] or 0
    return (
        round(total_mouse_movement, 0) if cursor else 0
    )  # Handle case where cursor is None


@app.route("/data")
async def get_data(request):
    global cached_data, cached_timestamp

    # Check if cached data exists and is fresh (within a reasonable timeframe)
    if (
        cached_data is None
        or (datetime.datetime.now() - cached_timestamp).total_seconds() > 60
    ):
        # If not cached or stale, fetch new data
        data = fetch_db_data(time_delta=datetime.timedelta(hours=24))
        cached_data = data  # Update cached data
        cached_timestamp = datetime.datetime.now()  # Update timestamp
    else:
        # If cached and fresh, return cached data
        data = cached_data

    return response.json(data)


@app.route("/style.css")
async def serve_style(request):
    style_path = Path(__file__).parent / "static" / "style.css"
    return await response.file(style_path)


@app.route("/script.js")
async def serve_script(request):
    script_path = Path(__file__).parent / "static" / "script.js"
    return await response.file(script_path)


@app.route("/")
async def index(request):
    index_path = Path(__file__).parent / "static" / "index.html"
    return await response.file(index_path)


if __name__ == "__main__":
    host = "10.0.0.200"
    port = 6930

    app.run(host=host, port=port)
