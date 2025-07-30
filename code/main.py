import cv2
import numpy as np
import json
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


# === CLASSIFIER ===

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


# === DART DETECTOR CLASS ===

def _estimate_tip(contour, frame_debug=None):
    # Fit rotated bounding box
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = box.astype(int)

    # Identify the longest edge (likely shaft direction)
    dists = [np.linalg.norm(box[i] - box[(i+1)%4]) for i in range(4)]
    idx = np.argmax(dists)
    pt1 = box[idx]
    pt2 = box[(idx + 1) % 4]

    # Normal vector (perpendicular to shaft edge)
    edge_vec = pt2 - pt1
    edge_vec = edge_vec / np.linalg.norm(edge_vec)
    normal_vec = np.array([-edge_vec[1], edge_vec[0]])

    max_proj = -np.inf
    tip = None
    for pt in contour:
        p = pt[0]
        proj = np.dot(p - pt1, normal_vec)
        if proj > max_proj:
            max_proj = proj
            tip = tuple(p)

    # === Debug image with visualization ===
    if frame_debug is not None:
        debug_img = frame_debug.copy()
        cv2.drawContours(debug_img, [contour], -1, (255, 0, 255), 2)
        cv2.circle(debug_img, tip, 6, (0, 255, 255), -1)
        cv2.line(debug_img, pt1, pt2, (255, 255, 0), 2)
        cv2.putText(debug_img, "TIP", (tip[0]+5, tip[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
        cv2.imshow("Detected Dart", debug_img)
        cv2.imwrite("last_detected_dart.png", debug_img)

    return tip

def _transform_points(points, matrix):
    if matrix is None or len(points) == 0:
        return []
    pts = np.array([[p] for p in points], dtype=np.float32)
    warped = cv2.perspectiveTransform(pts, np.linalg.inv(matrix))
    return [tuple(p[0]) for p in warped]

class DartDetector:
    def __init__(self, still_time=0.4, motion_thresh=40, min_blob_area=50):
        self.bg_frame = None
        self.last_movement = time.time()
        self.still_time = still_time
        self.motion_thresh = motion_thresh
        self.min_blob_area = min_blob_area
        self.detected_positions = []
        self.known_darts = []
        self.ready_to_analyze = False

        self.motion_history = []
        self.motion_history_duration = 0.5  # SHORTER!
        self.motion_min_level = 30          # LOWER!
        self.motion_max_jump = 60           # LOOSER!

    def update(self, frame, transform):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)

        if self.bg_frame is None:
            self.bg_frame = blurred.copy()
            return [], None, [], 0

        diff = cv2.absdiff(self.bg_frame, blurred)
        _, thresh = cv2.threshold(diff, self.motion_thresh, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        thresh = cv2.erode(thresh, None, iterations=1)

        # Mask known darts
        mask = np.ones_like(thresh) * 255
        for (x, y) in self.known_darts:
            cv2.circle(mask, (int(x), int(y)), 12, 0, -1)
        thresh = cv2.bitwise_and(thresh, thresh, mask=mask)

        motion_level = np.sum(thresh) / 255
        new_darts = []
        contour_boxes = []
        now = time.time()

        self.motion_history.append((now, motion_level))
        self.motion_history = [(t, l) for (t, l) in self.motion_history if now - t <= self.motion_history_duration]

        if len(self.motion_history) >= 3:
            levels = [l for (_, l) in self.motion_history]
            spread = max(levels) - min(levels)
            avg_level = sum(levels) / len(levels)

            if spread < self.motion_max_jump:
                self.last_movement = now
                self.ready_to_analyze = True

        if self.ready_to_analyze and (now - self.last_movement > self.still_time):
            print(f"[INFO] Still detected → analyzing darts (motion level: {motion_level:.1f})")
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"[INFO] Found {len(contours)} contours")

            for c in contours:
                area = cv2.contourArea(c)
                if area < self.min_blob_area:
                    continue

                (x, y, w, h) = cv2.boundingRect(c)
                contour_boxes.append((x, y, w, h))

                tip = _estimate_tip(c, frame_debug=frame)

                print(f"Tip estimate: {tip} | area: {area}")
                if tip == (0, 0):
                    continue

                if self._is_new_dart(tip):
                    self.known_darts.append(tip)
                    new_darts.append(tip)

                    self.ready_to_analyze = False
                    self.motion_history.clear()

                    break

            print(f"[INFO] New darts detected: {new_darts}" if new_darts else "[INFO] No new darts")
            self.bg_frame = blurred.copy()
            self.ready_to_analyze = False  # Only reset once

        canvas_coords = _transform_points(new_darts, transform)
        return canvas_coords, thresh, contour_boxes, motion_level

    def _is_new_dart(self, tip, min_dist=30):
        for known in self.known_darts:
            if np.linalg.norm(np.array(tip) - np.array(known)) < min_dist:
                return False
        return True

# === MAIN ===

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


def main():
    cap = cv2.VideoCapture(0)
    last_transform = None

    detector = DartDetector()
    print("Press 'q' to quit. Throw darts and watch for results...")

    def on_thresh_change(val):
        detector.motion_thresh = val

    cv2.namedWindow("Dart Classifier")
    cv2.createTrackbar("Threshold", "Dart Classifier", detector.motion_thresh, 100, on_thresh_change)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ArUco detection
        corners, ids, _ = aruco.detectMarkers(frame)
        if ids is not None and len(ids) >= 4:
            marker_dict = get_marker_corners_dict(corners, ids)
            if all(k in marker_dict for k in [0, 1, 2, 3]):
                last_transform = get_perspective_matrix(marker_dict)

        if last_transform is not None:
            canvas_coords, thresh_img, boxes, motion_level = detector.update(frame, last_transform)
        else:
            canvas_coords, thresh_img, boxes, motion_level = [], None, [], 0

        # Show motion level on screen
        cv2.putText(frame, f"Motion Level: {motion_level:.0f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Draw detection boxes
        for (x, y, w, h) in boxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "Blob", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 0, 255), 1)

        # Draw classification hits
        for (canvas_x, canvas_y) in canvas_coords:
            ring_ids = classify_ring(canvas_x, canvas_y)
            sector_id = classify_sector(canvas_x, canvas_y)
            field = classify_field(ring_ids, sector_id)
            print(f"Dart hit at ({canvas_x:.1f}, {canvas_y:.1f}) → {field}")
            screen_pt = cv2.perspectiveTransform(
                np.array([[[canvas_x, canvas_y]]], dtype=np.float32), last_transform)[0][0]
            cv2.circle(frame, (int(screen_pt[0]), int(screen_pt[1])), 6, (0, 255, 0), -1)
            cv2.putText(frame, field, (int(screen_pt[0] + 10), int(screen_pt[1])),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Draw known darts in white
        for x, y in detector.known_darts:
            cv2.circle(frame, (int(x), int(y)), 4, (255, 255, 255), -1)

        # Show threshold (diff) image to see motion areas
        if thresh_img is not None:
            cv2.imshow("Motion Detection Threshold", thresh_img)


        cv2.imshow("Dart Classifier", frame)

        if cv2.waitKey(30) & 0xFF == ord('r'):
            detector.bg_frame = None
            print("[DEBUG] Background reset")

        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
