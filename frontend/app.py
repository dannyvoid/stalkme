import os
import datetime
import sqlite3
from pathlib import Path
from sanic import Sanic, response

app = Sanic(__name__)

log_file = Path(__file__).parent.parent / "persistent" / "log.db"

cached_data = None
cached_timestamp = None

debug = True


async def fetch_db_data() -> dict:
    global cached_data, cached_timestamp

    start_time = datetime.datetime.now()
    data = {
        "clicks_left": 0,
        "clicks_right": 0,
        "clicks_middle": 0,
        "gamepad_actions": 0,
        "mouse_movement": 0,
        "key_presses": 0,
        "__current_time__": datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "__logging_since__": datetime.datetime.fromtimestamp(
            os.path.getctime(log_file.with_suffix(".csv"))
        ).strftime("%Y-%m-%d %I:%M:%S %p"),
        "__logging_size__": os.path.getsize(log_file) / 1024,
    }

    with sqlite3.connect(log_file) as conn:
        try:
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


def count_clicks(conn, event_type, button):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM events WHERE event = ? AND button = ?",
        (event_type, button),
    )
    return cursor.fetchone()[0]


def count_events(conn, event_type):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events WHERE event = ?", (event_type,))
    return cursor.fetchone()[0]


def calculate_mouse_movement(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(distance_in_inches) FROM events")
    total_mouse_movement = cursor.fetchone()[0] or 0
    return round(total_mouse_movement, 0)


@app.route("/data")
async def get_data(request):
    global cached_data, cached_timestamp

    # Check if cached data exists and is fresh (within a reasonable timeframe)
    if (
        cached_data is None
        or (datetime.datetime.now() - cached_timestamp).total_seconds() > 60
    ):
        # If not cached or stale, fetch new data
        data = await fetch_db_data()
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
