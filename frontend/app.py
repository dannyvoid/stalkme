import os
import uuid
import datetime
import pandas as pd
from pathlib import Path
from sanic import Sanic, response
from sanic.request import Request
import asyncio

app = Sanic(__name__)

active_sessions = set()
user_data = {}
session_last_activity = {}  # Store last activity time for each session ID

log_file = Path(__file__).parent.parent / "persistent" / "log.csv"

# Session expiry time in seconds (e.g., 30 minutes)
SESSION_EXPIRY_SECONDS = 30 * 60


def get_unique_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in active_sessions:
        session_id = str(uuid.uuid4())
    return session_id


def get_real_ip(request: Request):
    if "X-Forwarded-For" in request.headers:
        ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif "X-Real-IP" in request.headers:
        ip = request.headers.get("X-Real-IP")
    else:
        ip = request.ip
    return ip


async def expire_sessions():
    while True:
        await asyncio.sleep(60)  # Check every minute for expired sessions
        now = datetime.datetime.now()
        expired_sessions = []
        for session_id, last_activity in session_last_activity.items():
            if (now - last_activity).total_seconds() > SESSION_EXPIRY_SECONDS:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            active_sessions.discard(session_id)
            if session_id in user_data:
                del user_data[session_id]
            if session_id in session_last_activity:
                del session_last_activity[session_id]


@app.middleware("request")
async def track_active_users(request: Request):
    session_id = get_unique_session_id(request)
    active_sessions.add(session_id)
    request.ctx.session_id = session_id
    session_last_activity[session_id] = (
        datetime.datetime.now()
    )  # Update last activity time
    # Track additional user information
    user_data[session_id] = {
        "ip": get_real_ip(request),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
    }


@app.middleware("response")
async def add_session_cookie(request: Request, response):
    response.cookies.add_cookie("session_id", request.ctx.session_id)


async def parse_csv() -> dict:
    ct = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    since = datetime.datetime.fromtimestamp(os.path.getctime(log_file))
    since = since.strftime("%Y-%m-%d %I:%M:%S %p")
    size = os.path.getsize(log_file) / 1024

    data = {
        "clicks_left": 0,
        "clicks_right": 0,
        "clicks_middle": 0,
        "gamepad_actions": 0,
        "mouse_movement": 0,
        "key_presses": 0,
        "__current_time__": ct,
        "__logging_since__": since,
        "__logging_size__": size,
    }

    try:
        dtype = {"distance_in_inches": float}
        df = pd.read_csv(log_file, dtype=dtype)
    except pd.errors.EmptyDataError:
        print(f"Empty or unreadable file: {log_file}")
        return data
    except pd.errors.ParserError:
        print(f"Error parsing CSV file: {log_file}")
        return data
    except Exception as e:
        print(f"Unexpected error reading CSV file: {e}")
        return data

    data["clicks_left"] = df[
        (df["event"] == "Pressed") & (df["button"] == "Button.left")
    ].shape[0]
    data["clicks_right"] = df[
        (df["event"] == "Pressed") & (df["button"] == "Button.right")
    ].shape[0]
    data["clicks_middle"] = df[
        (df["event"] == "Pressed") & (df["button"] == "Button.middle")
    ].shape[0]
    data["key_presses"] = df[df["event"] == "Key Pressed"].shape[0]
    data["gamepad_actions"] = df[df["event"] == "Gamepad Pressed"].shape[0]
    data["mouse_movement"] = df["distance_in_inches"].sum()
    data["mouse_movement"] = round(data["mouse_movement"], 0)

    return data


@app.route("/data")
async def get_data(request):
    data = await parse_csv()
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


@app.route("/traffic")
async def serve_traffic(request):
    traffic_data = {"users": len(active_sessions), "user_data": user_data}
    return response.json(traffic_data)


if __name__ == "__main__":
    host = "10.0.0.200"
    port = 6930

    # Start session expiry background task
    app.add_task(expire_sessions())

    app.run(host=host, port=port)
