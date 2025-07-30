import cv2
import numpy as np
import time

distance_threshold = 70
groups = []

def _estimate_tip(contour, frame_debug=None):
    hull = cv2.convexHull(contour)
    if len(hull) < 3:
        return None

    pts = hull.reshape(-1, 2)
    centroid = np.mean(pts, axis=0)

    max_dist = 60
    filtered_pts = np.array([p for p in pts if np.linalg.norm(p - centroid) < max_dist])
    if len(filtered_pts) < 3:
        return None

    max_area = 0
    triangle = None
    for i in range(len(filtered_pts)):
        for j in range(i + 1, len(filtered_pts)):
            for k in range(j + 1, len(filtered_pts)):
                v1 = filtered_pts[j] - filtered_pts[i]
                v2 = filtered_pts[k] - filtered_pts[i]
                area = 0.5 * abs(v1[0] * v2[1] - v1[1] * v2[0])
                if area > max_area:
                    max_area = area
                    triangle = [filtered_pts[i], filtered_pts[j], filtered_pts[k]]

    if triangle is None:
        return None

    a, b, c = triangle
    dists = [
        (np.linalg.norm(a - b), c),
        (np.linalg.norm(a - c), b),
        (np.linalg.norm(b - c), a)
    ]
    dists.sort(key=lambda x: x[0])
    tip = tuple(dists[0][1].astype(int))

    if frame_debug is not None:
        debug_img = cv2.cvtColor(frame_debug.copy(), cv2.COLOR_GRAY2BGR)
        triangle_pts = [tuple(p.astype(int)) for p in triangle]
        cv2.polylines(debug_img, [np.array(triangle_pts)], isClosed=True, color=(0, 255, 255), thickness=1)
        cv2.circle(debug_img, tip, 6, (0, 0, 255), -1)
        cv2.circle(debug_img, tip, distance_threshold, (255, 255, 255), 1)
        cv2.imwrite("last_detected_dart.png", debug_img)

    return tip

class DartDetector:
    def __init__(self, still_time=0.4, motion_thresh=13, min_blob_area=50):
        self.bg_frame = None
        self.last_movement = time.time()
        self.still_time = still_time
        self.motion_thresh = motion_thresh
        self.min_blob_area = min_blob_area
        self.detected_positions = []
        self.known_darts = []
        self.ready_to_analyze = False

        self.motion_history = []
        self.motion_history_duration = 0.5
        self.motion_min_level = 30
        self.motion_max_jump = 60

        self.debug_tip = None
        self.debug_merged = None

    def update(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)

        if self.bg_frame is None:
            self.bg_frame = blurred.copy()
            return [], None, [], 0

        diff = cv2.absdiff(self.bg_frame, blurred)
        _, thresh = cv2.threshold(diff, self.motion_thresh, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        thresh = cv2.erode(thresh, None, iterations=1)

        mask = np.ones_like(thresh) * 255
        for (x, y) in self.known_darts:
            cv2.circle(mask, (int(x), int(y)), 12, (0,), -1)
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
            if spread < self.motion_max_jump:
                self.last_movement = now
                self.ready_to_analyze = True

        if motion_level > 10000:
            self.ready_to_analyze = False
            self.bg_frame = blurred.copy()
            self.known_darts.clear()
            return [], thresh, contour_boxes, motion_level

        if self.ready_to_analyze and (now - self.last_movement > self.still_time):
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            filtered = [c for c in contours if cv2.contourArea(c) >= self.min_blob_area]

            def contour_distance(c1, c2):
                min_dist = np.inf
                for p1 in c1:
                    for p2 in c2:
                        d = np.linalg.norm(p1[0] - p2[0])
                        if d < min_dist:
                            min_dist = d
                return min_dist

            used = set()

            for i, c1 in enumerate(filtered):
                if i in used:
                    continue
                group = [c1]
                used.add(i)
                queue = [i]
                while queue:
                    idx = queue.pop()
                    for j, c2 in enumerate(filtered):
                        if j in used:
                            continue
                        dist = contour_distance(filtered[idx], c2)
                        if dist < distance_threshold:
                            group.append(c2)
                            used.add(j)
                            queue.append(j)
                groups.append(group)

            groups.sort(key=lambda g: cv2.contourArea(np.vstack(g)), reverse=True)
            if groups:
                largest_group = groups[0]
                merged_contour = np.vstack(largest_group)
                tip = _estimate_tip(merged_contour, frame_debug=thresh)
                if tip is not None and self._is_new_dart(tip):
                    self.known_darts.append(tip)
                    new_darts.append(tip)
                    self.ready_to_analyze = False
                    self.motion_history.clear()

            self.bg_frame = blurred.copy()
            self.ready_to_analyze = False

        return new_darts, thresh, contour_boxes, motion_level

    def _is_new_dart(self, tip, min_dist=30):
        for known in self.known_darts:
            if np.linalg.norm(np.array(tip) - np.array(known)) < min_dist:
                return False
        return True

    def get_groups(self):
        return groups