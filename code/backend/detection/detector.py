import cv2
import numpy as np
import time

groups = []

def _estimate_tip(contour, frame_debug=None):
    if contour is None or len(contour) < 3:
        return None, None

    hull = cv2.convexHull(contour)
    pts = hull.reshape(-1, 2)

    centroid = np.mean(pts, axis=0)

    left_idx = np.argmin(pts[:, 0])
    tip = tuple(pts[left_idx].astype(int))

    if frame_debug is not None:
        debug_img = cv2.cvtColor(frame_debug.copy(), cv2.COLOR_GRAY2BGR)
        cv2.circle(debug_img, tip, 6, (0, 0, 255), -1)
        cv2.circle(debug_img, (int(centroid[0]), int(centroid[1])), 5, (255, 0, 0), -1)
        cv2.imwrite("last_detected_dart.png", debug_img)

    return tip, centroid

class DartDetector:
    def __init__(self, still_time=0.4, motion_thresh=18, min_blob_area=50, debug=False):
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
        self.debug = debug
        self.debug_frame_id = 0

    def _apply_filter_pipeline(self, diff):
        blur = cv2.GaussianBlur(diff, (5, 5), 0)

        for i in range(10):
            blur = cv2.GaussianBlur(blur, (9, 9), 1)

        blur = cv2.bilateralFilter(blur, 9, 75, 75)

        gray = blur

        _, thresh = cv2.threshold(gray, self.motion_thresh, 255, 0)
        return thresh

    def create_filter_images(self, diff):
        if self.debug:
            self._debug_save("10_diff_input", diff)

        blur = cv2.GaussianBlur(diff, (5, 5), 0)
        if self.debug:
            self._debug_save("11_blur_1", blur)

        # for i in range(10):
        #     blur = cv2.GaussianBlur(blur, (9, 9), 1)
        #     if self.debug:
        #         self._debug_save(f"12_blur_iter_{i:02d}", blur)

        blur = cv2.bilateralFilter(blur, 9, 75, 75)
        if self.debug:
            self._debug_save("13_bilateral", blur)

        gray = blur
        if self.debug:
            self._debug_save("14_gray_pre_thresh", gray)

        _, thresh = cv2.threshold(gray, self.motion_thresh, 255, 0)
        if self.debug:
            self._debug_save("15_thresh_raw", thresh)

    def _connect_dart_parts(self, thresh):
        kernel_long = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 5))
        connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_long)

        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        connected = cv2.morphologyEx(connected, cv2.MORPH_CLOSE, kernel_small)

        if self.debug:
            self._debug_save("18_connected", connected)

        return connected

    def update(self, frame, ignore_mask=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)

        if self.bg_frame is None:
            self.bg_frame = blurred.copy()
            return [], None, [], 0

        diff = cv2.absdiff(self.bg_frame, blurred)

        thresh = self._apply_filter_pipeline(diff)

        thresh = cv2.dilate(thresh, None, iterations=2)
        thresh = cv2.erode(thresh, None, iterations=1)

        thresh = self._connect_dart_parts(thresh)

        if ignore_mask is not None:
            try:
                mask = ignore_mask
                if not isinstance(mask, np.ndarray):
                    mask = np.array(mask)
                if mask.dtype != np.bool_:
                    mask = mask.astype(np.uint8)
                    mask = mask != 0

                if mask.shape != thresh.shape:
                    mask_resized = cv2.resize(mask.astype('uint8'), (thresh.shape[1], thresh.shape[0]), interpolation=cv2.INTER_NEAREST)
                    mask = mask_resized != 0

                if mask.any():
                    thresh = thresh.copy()
                    thresh[mask] = 0
            except Exception:
                pass

        known_mask = np.ones_like(thresh) * 255
        for (x, y) in self.known_darts:
            cv2.circle(known_mask, (int(x), int(y)), 12, (0,), -1)
        thresh = cv2.bitwise_and(thresh, thresh, mask=known_mask)

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
            self._debug_save("01_input", frame)
            self._debug_save("02_diff_global", diff)
            self._debug_save("03_thresh_global", thresh)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            contours = [c for c in contours if cv2.contourArea(c) >= self.min_blob_area]
            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            if self.debug:
                dbg = frame.copy()
                for c in contours[:3]:
                    if c is not None and len(c) > 0:
                        cv2.drawContours(dbg, [c], -1, (0, 255, 0), 2)
                self._debug_save("04_largest_contours", dbg)

            if contours:
                try:
                    all_pts = np.vstack([c.reshape(-1, 2) for c in contours])
                    all_pts = all_pts.astype(np.float32)
                except Exception:
                    all_pts = None

                merged_contour = None
                tip = None
                centroid = None

                if all_pts is not None and len(all_pts) >= 3:
                    merged_contour = cv2.convexHull(all_pts.reshape(-1, 1, 2))
                    tip, centroid = _estimate_tip(merged_contour, frame_debug=thresh)

                if (tip is None or centroid is None) and isinstance(all_pts, np.ndarray) and all_pts.shape[0] > 0:
                    left_idx = int(np.argmin(all_pts[:, 0]))
                    x = float(all_pts[left_idx, 0].tolist())
                    y = float(all_pts[left_idx, 1].tolist())
                    tip = (int(x), int(y))
                    centroid = np.mean(all_pts, axis=0)

                if tip is not None and centroid is not None:
                    if tip[0] >= centroid[0]:
                        return [], thresh, contour_boxes, motion_level

                    if self._is_new_dart(tip):
                        self.known_darts.append(tip)
                        new_darts.append(tip)
                        self.ready_to_analyze = False

                        debug_final = frame.copy()
                        cv2.circle(debug_final, tip, 8, (0, 0, 255), -1)
                        cv2.circle(debug_final, tip, 22, (0, 255, 255), 2)
                        cv2.putText(debug_final, "DART", (tip[0] + 10, tip[1] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                        try:
                            if merged_contour is not None and merged_contour.shape[0] > 0:
                                dbg_merged = frame.copy()
                                cv2.drawContours(dbg_merged, [merged_contour], -1, (255, 0, 0), 2)
                                cv2.circle(dbg_merged, tip, 6, (0, 0, 255), -1)
                                self._debug_save("04_largest_contours_merged", dbg_merged)
                        except Exception:
                            print("Error drawing merged contour for debug")
                            pass

                        self._debug_save("05_final_tip", debug_final)

                        self.create_filter_images(diff)

                        self.debug_frame_id += 1
                        self.motion_history.clear()

            self.bg_frame = blurred.copy()
            self.ready_to_analyze = False

        return new_darts, thresh, contour_boxes, motion_level

    def _is_new_dart(self, tip, min_dist=30):
        return True
        # for known in self.known_darts:
        #     if np.linalg.norm(np.array(tip) - np.array(known)) < min_dist:
        #         return False
        # return True

    def get_groups(self):
        return groups

    def _debug_save(self, name, img):
        if not self.debug:
            return
        filename = f"debug/{self.debug_frame_id:05d}_{name}.png"
        cv2.imwrite(filename, img)
