import json
import cv2
import numpy as np
import math
import time

# === Load ring + sector data ===
with open("rings.json", "r") as f:
    ring_data = json.load(f)

with open("sectors.json", "r") as f:
    sector_config = json.load(f)

NUM_RINGS = len(ring_data)
NUM_SECTORS = 20
canvas_size = (500, 500)

DARTBOARD_NUMBERS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17,
                     3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

# === ArUco Setup ===
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
aruco = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# === Stabilization state ===
last_transform = None
last_update_time = 0
update_interval = 3  # seconds

clicked_canvas_pos = None
clicked_screen_pos = None

def draw_map(highlight_rings=None, highlight_sector=None):
    img = np.zeros((canvas_size[1], canvas_size[0], 3), dtype=np.uint8)

    for i, ring in enumerate(ring_data):
        cx, cy = ring['cx'], ring['cy']
        axes = (int(ring['scale'] * ring['stretch_x']), int(ring['scale'] * ring['stretch_y']))
        color = (0, 0, 255) if highlight_rings and i in highlight_rings else (200, 200, 200)
        cv2.ellipse(img, (int(cx), int(cy)), axes, 0, 0, 360, color, 2)

    outer_ring = ring_data[0]
    cx = outer_ring['cx'] + sector_config['offset_x']
    cy = outer_ring['cy'] + sector_config['offset_y']
    axes_x = int(outer_ring['scale'] * outer_ring['stretch_x'])
    axes_y = int(outer_ring['scale'] * outer_ring['stretch_y'])

    rotation_offset = ((sector_config['rotation']) + 360) % 360 - 108

    for i in range(NUM_SECTORS):
        angle_deg = i * (360 / NUM_SECTORS) + rotation_offset
        angle_rad = math.radians(angle_deg)
        dx = math.cos(angle_rad) * axes_x
        dy = math.sin(angle_rad) * axes_y
        pt1 = (int(cx), int(cy))
        pt2 = (int(cx + dx), int(cy + dy))

        if i == 0:
            color = (255, 0, 0)
            thickness = 2
        elif highlight_sector == i:
            color = (0, 255, 0)
            thickness = 2
        else:
            color = (100, 100, 255)
            thickness = 1

        cv2.line(img, pt1, pt2, color, thickness)

    return img

def classify_ring(x, y):
    for i in range(NUM_RINGS - 1):
        outer = ring_data[i]
        inner = ring_data[i + 1]
        if point_in_ellipse(x, y, outer) and not point_in_ellipse(x, y, inner):
            return [i, i + 1]
    if point_in_ellipse(x, y, ring_data[-1]):
        return [NUM_RINGS - 1]
    return [0]

def point_in_ellipse(x, y, ring):
    dx = x - ring['cx']
    dy = y - ring['cy']
    nx = dx / (ring['scale'] * ring['stretch_x'])
    ny = dy / (ring['scale'] * ring['stretch_y'])
    return nx ** 2 + ny ** 2 <= 1

def classify_sector(x, y):
    outer_ring = ring_data[0]
    cx = outer_ring['cx'] + sector_config['offset_x']
    cy = outer_ring['cy'] + sector_config['offset_y']
    dx = x - cx
    dy = y - cy
    angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
    angle = (angle - (sector_config['rotation']) + 360) % 360 + 108
    if angle > 360:
        angle -= 360
    return int(angle // (360 / NUM_SECTORS))

def classify_field(ring_ids, sector_id):
    if 0 in ring_ids and len(ring_ids) == 1:
        return "0 (outside)"
    if len(ring_ids) == 1 and ring_ids[0] == 5:
        return "bullseye"

    outer, inner = (ring_ids[0], ring_ids[1]) if len(ring_ids) == 2 else (ring_ids[0], None)
    number = DARTBOARD_NUMBERS[sector_id]

    if outer == 0 and inner == 1:
        return f"double {number}"
    elif outer == 1 and inner == 2:
        return f"single {number} (outer)"
    elif outer == 2 and inner == 3:
        return f"triple {number}"
    elif outer == 3 and inner == 4:
        return f"single {number} (inner)"
    elif outer == 4 and inner == 5:
        return f"outer bull"
    return f"single {number}"

def get_marker_corners_dict(corners, ids):
    return {id_[0]: c[0] for c, id_ in zip(corners, ids)}

def get_perspective_matrix(corners_dict):
    src_pts = np.array([[0, 0], [canvas_size[0], 0], [canvas_size[0], canvas_size[1]], [0, canvas_size[1]]], dtype=np.float32)
    dst_pts = np.array([
        corners_dict[0][0],
        corners_dict[1][1],
        corners_dict[3][2],
        corners_dict[2][3],
    ], dtype=np.float32)
    return cv2.getPerspectiveTransform(src_pts, dst_pts)

def run_camera_classifier():
    global last_transform, last_update_time, clicked_canvas_pos, clicked_screen_pos

    cap = cv2.VideoCapture(0)
    print("Press 'q' to quit, click on screen to classify.")

    cv2.namedWindow("Dartboard Classifier")

    def on_mouse(event, x, y, flags, param):
        global clicked_canvas_pos, clicked_screen_pos
        if event == cv2.EVENT_LBUTTONDOWN and last_transform is not None:
            inv_matrix = np.linalg.inv(last_transform)
            point = np.array([[[x, y]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(point, inv_matrix)[0][0]
            clicked_canvas_pos = transformed
            clicked_screen_pos = (x, y)

    cv2.setMouseCallback("Dartboard Classifier", on_mouse)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ArUco detection
        corners, ids, _ = aruco.detectMarkers(frame)

        now = time.time()
        if ids is not None and len(ids) >= 4:
            marker_dict = get_marker_corners_dict(corners, ids)
            if all(k in marker_dict for k in [0, 1, 2, 3]) and now - last_update_time > update_interval:
                last_transform = get_perspective_matrix(marker_dict)
                last_update_time = now

        canvas = draw_map()

        if last_transform is not None:
            warped = cv2.warpPerspective(canvas, last_transform, (frame.shape[1], frame.shape[0]))
            mask = warped > 0
            frame[mask] = warped[mask]

            if clicked_canvas_pos is not None and clicked_screen_pos is not None:
                ring_ids = classify_ring(*clicked_canvas_pos)
                sector_id = classify_sector(*clicked_canvas_pos)
                result = classify_field(ring_ids, sector_id)
                cv2.circle(frame, clicked_screen_pos, 6, (0, 0, 255), -1)
                print(f"Click: {clicked_canvas_pos} → {result}")
                clicked_canvas_pos = None
                clicked_screen_pos = None

        cv2.imshow("Dartboard Classifier", frame)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

run_camera_classifier()
