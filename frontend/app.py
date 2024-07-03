import os
import datetime
import pandas as pd
from pathlib import Path
from sanic import Sanic, response

app = Sanic(__name__)

log_file = Path(__file__).parent.parent / "persistent" / "log.csv"


async def parse_csv() -> dict:
    ct = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    since = datetime.datetime.fromtimestamp(os.path.getctime(log_file))
    since = since.strftime("%Y-%m-%d %I:%M:%S %p")
    size = os.path.getsize(log_file) / 1024

    data = {
        "clicks_left": 0,
        "clicks_right": 0,
        "clicks_middle": 0,
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

    if "distance_in_inches" in df.columns:
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


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 6930
    app.run(host=host, port=port)
