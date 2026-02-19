import os
from threading import Thread
from time import sleep

import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from classifier import classify_ring, classify_sector, classify_field
from detector import DartDetector
from draw_canvas import draw_ellipses, draw_sector_lines
from file_handler import load_rings, load_lines, save_rings, save_lines

hover_pos = None

ring_data = load_rings()
sector_config = load_lines()
NUM_RINGS = len(ring_data)

clicked_points = []
canvas_size = None

camera_active = False
current_cap = None
stop_camera_flag = False
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


def hover_callback(event, x, y, flags, param):
    global hover_pos
    if event == cv2.EVENT_MOUSEMOVE:
        hover_pos = (x, y)


def select_camera(max_cams=5):
    caps = []
    for i in range(max_cams):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            caps.append((i, cap))
        else:
            cap.release()
    if not caps:
        print("No cameras found.")
        return None

    print("Press the number key for the camera you want to use.")
    while True:
        for idx, (i, cap) in enumerate(caps):
            ret, frame = cap.read()
            if ret:
                cv2.imshow(f"Camera {i}", frame)
        key = cv2.waitKey(1) & 0xFF
        if ord('0') <= key < ord('0') + len(caps):
            selected = key - ord('0')
            cam_idx = caps[selected][0]
            break

    for i, cap in caps:
        cap.release()
        cv2.destroyWindow(f"Camera {i}")
    return cam_idx


def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_points.append((x, y))
        ring_ids = classify_ring(x, y)
        sector_id = classify_sector(x, y)
        field = classify_field(ring_ids, sector_id)
        print(f"[Click] Point at ({x}, {y}) → {field}")

        data = {"score": field, "coords": {"x": x, "y": y}}
        socketio.emit("dart_hit", data)
        print(f"[WS] Sent click data: {data}")

def draw_virtual_canvas():
    canvas = np.zeros((
        canvas_size[1],
        canvas_size[0],
        3
    ), dtype=np.uint8)

    draw_ellipses(canvas, ring_data)

    draw_sector_lines(
        canvas,
        ring_data[0],
        sector_config[0],
        sector_config[1],
        sector_config[2],
        sector_config[3],
        sector_config[4],
        sector_config[5]
    )

    return canvas


@app.route("/")
def index():
    return "Dart detection backend running"


@app.post("/calibrate")
def calibrate():
    try:
        data = request.get_json(force=True)
        rings = data.get("rings", [])
        lines = data.get("lines", {}) if isinstance(data.get("lines", {}), dict) else {}

        rings_for_save = []
        for r in rings:
            try:
                cx = float(r["x"])
                cy = float(r["y"])
                scale = float(r["radius"])
                stretch_x = float(r.get("scaleX", 1.0))
                stretch_y = float(r.get("scaleY", 1.0))
                rings_for_save.append([cx, cy, scale, stretch_x, stretch_y])
            except Exception as e:
                print("[WS] Bad ring entry:", r, "error:", e)

        save_rings(rings_for_save)
        save_lines(
            float(lines.get("rotation", 0.0)),
            float(lines.get("offsetX", 0.0)),
            float(lines.get("offsetY", 0.0)),
            float(lines.get("scale", 1.0)),
            float(lines.get("stretchX", 1.0)),
            float(lines.get("stretchY", 1.0)),
        )

        print("[POST] Calibration saved")
        sleep(3)

        Thread(target=main, daemon=True).start()

        return jsonify({"type": "saved", "msg": "Calibration saved"})
    except Exception as e:
        print("[POST] save error:", e)
        return jsonify({"type": "error", "msg": f"Failed to save calibration: {e}"}), 500


@app.get("/close_camera")
def close_camera():
    global current_cap, stop_camera_flag, camera_active

    if not camera_active:
        return jsonify({"status": "no_camera_active"})

    stop_camera_flag = True  # Tell main loop to stop

    if current_cap is not None:
        try:
            current_cap.release()
            current_cap = None
        except Exception as e:
            print("Error releasing camera:", e)

    camera_active = False

    # Close any OpenCV windows
    try:
        cv2.destroyAllWindows()
    except:
        pass

    return jsonify({"status": "camera_closed"})


@app.get("/last_calibration")
def get_last_calibration():
    try:
        rings, _ = load_rings()
        lines = load_lines()
        return jsonify({
            "rings": [
                {
                    "x": float(r[0]),
                    "y": float(r[1]),
                    "radius": float(r[2]),
                    "scaleX": float(r[3]),
                    "scaleY": float(r[4])
                } for r in rings
            ],
            "lines": {
                "rotation": float(lines[0]),
                "offsetX": float(lines[1]),
                "offsetY": float(lines[2]),
                "scale": float(lines[3]),
                "stretchX": float(lines[4]),
                "stretchY": float(lines[5]),
            }
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load calibration {e}"}), 500


def main():
    Y_OFFSET = 0
    global canvas_size, current_cap, camera_active, stop_camera_flag

    stop_camera_flag = False
    cam_index = select_camera()
    if cam_index is None:
        return

    cap = cv2.VideoCapture(cam_index)
    current_cap = cap
    camera_active = True

    ret, frame = cap.read()
    if not ret:
        print("Failed to read from camera.")
        camera_active = False
        return

    global ring_data, sector_config
    ring_data, _ = load_rings()
    print(ring_data)
    sector_config = load_lines()
    print(sector_config)

    for ring in ring_data:
        ring[1] -= Y_OFFSET

    new_sectors = []
    for sector in sector_config:
        if isinstance(sector, (tuple, list)) and len(sector) >= 4:
            if len(sector) == 6:
                x1, y1, x2, y2, sx, sy = sector
                new_sectors.append((x1, y1 - Y_OFFSET, x2, y2 - Y_OFFSET, sx, sy))
            elif len(sector) == 4:
                x1, y1, x2, y2 = sector
                new_sectors.append((x1, y1 - Y_OFFSET, x2, y2 - Y_OFFSET))
            else:
                new_sectors.append(sector)
        else:
            new_sectors.append(sector)

    sector_config = new_sectors

    canvas_size = (frame.shape[1], frame.shape[0])
    detector = DartDetector(debug=True)
    print("Press 'q' to quit. Throw darts and watch for results...")

    cv2.namedWindow("Dartboard View")
    cv2.setMouseCallback("Dartboard View", hover_callback)
    cv2.createTrackbar("Threshold", "Dartboard View", detector.motion_thresh, 100,
                       lambda val: setattr(detector, "motion_thresh", val))

    while not stop_camera_flag:
        ret, raw_frame = cap.read()
        if not ret:
            break

        proc_frame = raw_frame.copy()
        vis_frame = raw_frame.copy()

        virtual_canvas = draw_virtual_canvas()
        mask = virtual_canvas[:, :, 1] > 0
        vis_frame[mask] = virtual_canvas[mask]

        if hover_pos is not None:
            hx, hy = hover_pos

            if 0 <= hx < frame.shape[1] and 0 <= hy < frame.shape[0]:
                ring_ids = classify_ring(hx, hy)
                sector_id = classify_sector(hx, hy)
                field = classify_field(ring_ids, sector_id)

                print(f"[Hover] ({hx}, {hy}) -> {field}")

                cv2.putText(
                    frame,
                    f"Hover Score: {field}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

        new_darts, thresh_img, boxes, motion_level = detector.update(proc_frame)

        cv2.putText(vis_frame, f"Motion Level: {motion_level:.0f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        for (x, y, w, h) in boxes:
            cv2.rectangle(vis_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(vis_frame, "Blob", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        for (x, y) in clicked_points:
            cv2.circle(vis_frame, (x, y), 3, (255, 0, 255), -1)

        for (x, y) in new_darts:
            ring_ids = classify_ring(int(x), int(y))
            sector_id = classify_sector(int(x), int(y))
            score = classify_field(ring_ids, sector_id)
            data = {"score": score, "coords": {"x": int(x), "y": int(y)}}
            socketio.emit("dart_hit", data)
            print(f"[Auto] Sent: {data}")

        for (x, y) in detector.known_darts:
            cv2.circle(vis_frame, (int(x), int(y)), 3, (255, 0, 0), -1)

        thresh_display = cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGR) if thresh_img is not None else np.zeros_like(vis_frame)
        thresh_display = cv2.resize(thresh_display, (vis_frame.shape[1], vis_frame.shape[0]))

        debug_merged = vis_frame.copy()
        for group in detector.get_groups():
            cv2.drawContours(debug_merged, group, -1, (0, 255, 255), 2)

        if os.path.exists("last_detected_dart.png"):
            debug_tip = cv2.imread("last_detected_dart.png", cv2.IMREAD_COLOR)
            if debug_tip is None:
                debug_tip = np.zeros_like(debug_merged)
            else:
                debug_tip = cv2.resize(
                    debug_tip,
                    (debug_merged.shape[1], debug_merged.shape[0])
                )
        else:
            debug_tip = np.zeros_like(debug_merged)

        debug_tip = cv2.resize(debug_tip, (debug_merged.shape[1],
                                           debug_merged.shape[0])) if debug_tip is not None else np.zeros_like(
            debug_merged)
        top_row = np.hstack((vis_frame, thresh_display))
        bottom_row = np.hstack((debug_tip, debug_merged))

        combined_view = np.vstack((top_row, bottom_row))

        cv2.imshow("Dartboard View", combined_view)

        key = cv2.waitKey(30)
        if key == ord('r'):
            detector.bg_frame = None
            clicked_points.clear()
            print("[DEBUG] Background reset")
        elif key == ord('q'):
            break

    cap.release()
    current_cap = None
    camera_active = False
    cv2.destroyAllWindows()
    if os.path.exists("last_detected_dart.png"):
        os.remove("last_detected_dart.png")


if __name__ == "__main__":
    os.makedirs("debug", exist_ok=True)
    Thread(target=main, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
