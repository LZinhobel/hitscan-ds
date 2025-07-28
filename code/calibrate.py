import cv2
import cv2.aruco as aruco
import numpy as np
from file_handler import *

NUM_RINGS = 6
canvas_size = (500, 500)

rings = []
current_ring = 0
last_valid_markers = {}

auto_generated = False
mode = "rings"
rings_loaded = False

line_rotation = 0.0
line_offset_x = 0.0
line_offset_y = 0.0
line_scale = 0.0
line_stretch_x = 0.0
line_stretch_y = 0.0

def get_marker_centers(corners, ids):
    marker_dict = {}
    for i, marker_id in enumerate(ids.flatten()):
        pts = corners[i][0]
        center = np.mean(pts, axis=0)
        marker_dict[marker_id] = center
    return marker_dict

def get_marker_corners_dict(corners, ids):
    return {id_[0]: c[0] for c, id_ in zip(corners, ids)}

def draw_virtual_canvas(marker_preview=None, show_lines=False):
    canvas = np.zeros((canvas_size[1], canvas_size[0], 3), dtype=np.uint8)

    for i in range(current_ring + 1):
        ring = rings[i]
        color = (0, 255, 0) if i == current_ring else (255, 255, 255)
        center = tuple(ring[0:2].astype(int))
        axes = (int(ring[2] * ring[3]), int(ring[2] * ring[4]))
        cv2.ellipse(canvas, center, axes, 0, 0, 360, color, 2)

    if show_lines:
        outer_ring = rings[0]
        cx, cy = outer_ring[0:2]
        radius = outer_ring[2] * max(outer_ring[3], outer_ring[4])
        for i in range(20):
            angle = np.deg2rad(i * 18 + line_rotation - 90)

            scaled_cos = np.cos(angle) * outer_ring[3] * line_scale * line_stretch_x
            scaled_sin = np.sin(angle) * outer_ring[4] * line_scale * line_stretch_y

            x = int(cx + radius * scaled_cos + line_offset_x)
            y = int(cy + radius * scaled_sin + line_offset_y)

            if i == 0:
                cv2.line(canvas, (int(cx) + int(line_offset_x), int(cy) + int(line_offset_y)), (x, y), (255, 0, 0), 1)
            else:
                cv2.line(canvas, (int(cx) + int(line_offset_x), int(cy) + int(line_offset_y)), (x, y), (100, 100, 255), 1)
    if marker_preview:
        for id_, pt in marker_preview.items():
            x, y = int(pt[0] / 2), int(pt[1] / 2)
            cv2.circle(canvas, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(canvas, f"ID {id_}", (x+6, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    return canvas

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

def handle_ring_keys(key, ring):
    global current_ring, auto_generated, rings, rings_loaded, mode

    MOVE_STEP = 1
    SCALE_STEP = 1
    STRETCH_STEP = 0.005

    key_actions = {
        ord('w'): lambda: ring.__setitem__(1, ring[1] - MOVE_STEP),
        ord('s'): lambda: ring.__setitem__(1, ring[1] + MOVE_STEP),
        ord('a'): lambda: ring.__setitem__(0, ring[0] - MOVE_STEP),
        ord('d'): lambda: ring.__setitem__(0, ring[0] + MOVE_STEP),
        ord('+'): lambda: ring.__setitem__(2, ring[2] + SCALE_STEP),
        ord('='): lambda: ring.__setitem__(2, ring[2] + SCALE_STEP),
        ord('-'): lambda: ring.__setitem__(2, max(10, ring[2] - SCALE_STEP)),
        ord('i'): lambda: ring.__setitem__(4, ring[4] + STRETCH_STEP),
        ord('k'): lambda: ring.__setitem__(4, max(0.1, ring[4] - STRETCH_STEP)),
        ord('l'): lambda: ring.__setitem__(3, ring[3] + STRETCH_STEP),
        ord('j'): lambda: ring.__setitem__(3, max(0.1, ring[3] - STRETCH_STEP)),
    }

    if key in key_actions:
        key_actions[key]()
    elif key == ord('n'):
        if current_ring == 0 and not auto_generated and not rings_loaded:
            base = rings[0].copy()
            scale_factors = [1.0, 0.85, 0.6, 0.55, 0.15, 0.06]
            for i in range(1, NUM_RINGS):
                rings[i] = np.array([base[0], base[1], base[2] * scale_factors[i], base[3], base[4]], dtype=np.float32)
            print("Inner rings auto-generated.")
            auto_generated = True

        current_ring += 1
        if current_ring >= NUM_RINGS:
            save_rings(rings)
            print("All rings placed and saved.\nNow editing field lines.")
            current_ring = NUM_RINGS - 1
            mode = "lines"
        else:
            print(f"Now editing ring {current_ring + 1} of {NUM_RINGS}")

def handle_line_keys(key):
    global line_offset_x, line_offset_y, line_rotation
    global line_scale, line_stretch_x, line_stretch_y

    MOVE_STEP = 1
    SCALE_STEP = 0.005
    ROTATE_STEP = 1

    key_actions = {
        ord('a'): lambda: setattr_nonlocal('line_offset_x', line_offset_x - MOVE_STEP),
        ord('d'): lambda: setattr_nonlocal('line_offset_x', line_offset_x + MOVE_STEP),
        ord('w'): lambda: setattr_nonlocal('line_offset_y', line_offset_y - MOVE_STEP),
        ord('s'): lambda: setattr_nonlocal('line_offset_y', line_offset_y + MOVE_STEP),
        ord('j'): lambda: setattr_nonlocal('line_stretch_x', max(0.1, line_stretch_x - SCALE_STEP)),
        ord('l'): lambda: setattr_nonlocal('line_stretch_x', line_stretch_x + SCALE_STEP),
        ord('i'): lambda: setattr_nonlocal('line_stretch_y', line_stretch_y + SCALE_STEP),
        ord('k'): lambda: setattr_nonlocal('line_stretch_y', max(0.1, line_stretch_y - SCALE_STEP)),
        ord('r'): lambda: setattr_nonlocal('line_rotation', line_rotation - ROTATE_STEP),
        ord('t'): lambda: setattr_nonlocal('line_rotation', line_rotation + ROTATE_STEP),
        ord('+'): lambda: setattr_nonlocal('line_scale', line_scale + SCALE_STEP),
        ord('='): lambda: setattr_nonlocal('line_scale', line_scale + SCALE_STEP),
        ord('-'): lambda: setattr_nonlocal('line_scale', max(0.1, line_scale - SCALE_STEP)),
        ord('n'): lambda: (save_lines(line_rotation, line_offset_x, line_offset_y, line_scale, line_stretch_x, line_stretch_y), print("Field lines saved.\nConfiguration complete. Press 'q' to exit.")),
    }

    if key in key_actions:
        key_actions[key]()

def setattr_nonlocal(name, value):
    globals()[name] = value

def detect_and_run():
    global current_ring, last_valid_markers, auto_generated, mode, line_stretch_y, line_stretch_x
    global line_offset_x, line_offset_y, line_rotation, line_scale, rings, rings_loaded

    last_valid_corners = {}

    cam_index = select_camera()
    if cam_index is None:
        return

    cap = cv2.VideoCapture(cam_index)
    rings, rings_loaded = load_rings()
    line_rotation, line_offset_x, line_offset_y, line_scale, line_stretch_x, line_stretch_y = load_lines()

    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    parameters.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    print_controls()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        corners, ids, _ = detector.detectMarkers(frame)

        if ids is not None and len(ids) >= 4:
            marker_centers = get_marker_centers(corners, ids)
            marker_corners = get_marker_corners_dict(corners, ids)

            if all(mid in marker_centers for mid in [0, 1, 2, 3]):
                last_valid_markers = marker_centers.copy()
                last_valid_corners = marker_corners.copy()

        virtual_canvas = draw_virtual_canvas(last_valid_markers, show_lines=(mode == "lines"))

        if all(mid in last_valid_corners for mid in [0, 1, 2, 3]):
            src_pts = np.array([[0, 0], [canvas_size[0], 0], [canvas_size[0], canvas_size[1]], [0, canvas_size[1]]], dtype=np.float32)
            dst_pts = np.array([
                last_valid_corners[0][0],
                last_valid_corners[1][1],
                last_valid_corners[3][2],
                last_valid_corners[2][3],
            ], dtype=np.float32)

            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            warped = cv2.warpPerspective(virtual_canvas, matrix, (frame.shape[1], frame.shape[0]))

            mask = warped[:, :, 1] > 0
            frame[mask] = warped[mask]

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)

        cv2.imshow("Live Feed with Rings", frame)
        cv2.imshow("Virtual Canvas Preview", virtual_canvas)

        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            break

        if mode == "rings":
            handle_ring_keys(key, rings[current_ring])
        elif mode == "lines":
            handle_line_keys(key)

    cap.release()
    cv2.destroyAllWindows()

def print_controls():
    print("Controls:")
    print("  Ring Mode (Rings):")
    print("    W/A/S/D - Move ring")
    print("    +/-     - Resize radius")
    print("    I/K     - Stretch Y")
    print("    J/L     - Stretch X")
    print("    N       - Next ring or enter line mode")
    print("  Line Mode:")
    print("    W/A/S/D - Move all lines")
    print("    +/-     - Scale all lines")
    print("    R/T     - Rotate all lines")
    print("    I/K     - Stretch Y")
    print("    J/L     - Stretch Y")
    print("  Q         - Quit")


if __name__ == "__main__":
    detect_and_run()
