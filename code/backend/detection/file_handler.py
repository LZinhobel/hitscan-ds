import os
import json
import numpy as np

RINGS_SAVE_PATH = "rings.json"
LINES_SAVE_PATH = "sectors.json"

NUM_RINGS = 6

def save_rings(rings):
    json_rings = [
        {
            "cx": float(r[0]),
            "cy": float(r[1]),
            "scale": float(r[2]),
            "stretch_x": float(r[3]),
            "stretch_y": float(r[4])
        } for r in rings
    ]
    with open(RINGS_SAVE_PATH, "w") as f:
        json.dump(json_rings, f, indent=2)
    return True

def save_lines(rotation, offset_x, offset_y, scale, stretch_x, stretch_y):
    lines_data = {
        "rotation": rotation,
        "offset_x": offset_x,
        "offset_y": offset_y,
        "scale": scale,
        "stretch_x": stretch_x,
        "stretch_y": stretch_y
    }
    with open(LINES_SAVE_PATH, "w") as f:
        json.dump(lines_data, f, indent=2)
    return True

def load_rings():
    if os.path.exists(RINGS_SAVE_PATH):
        with open(RINGS_SAVE_PATH, "r") as f:
            data = json.load(f)
            rings = [np.array([
                ring["cx"],
                ring["cy"],
                ring["scale"],
                ring["stretch_x"],
                ring["stretch_y"]
            ], dtype=np.float32) for ring in data]
            return rings, True
    else:
        return [np.array([250, 250, 80, 1.0, 1.0], dtype=np.float32) for _ in range(NUM_RINGS)], False

def load_lines():
    if os.path.exists(LINES_SAVE_PATH):
        with open(LINES_SAVE_PATH, "r") as f:
            lines_data = json.load(f)
            return (
                lines_data.get("rotation", 0.0),
                lines_data.get("offset_x", 0),
                lines_data.get("offset_y", 0),
                lines_data.get("scale", 1.0),
                lines_data.get("stretch_x", 1.0),
                lines_data.get("stretch_y", 1.0),
            )
    else:
        return 0.0, 0, 0, 1.0, 1.0, 1.0
