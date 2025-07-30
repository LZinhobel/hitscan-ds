import cv2
from file_handler import *
from classifier import *
from detector import DartDetector
from draw_canvas import draw_ellipses, draw_sector_lines

ring_data, rings_loaded = load_rings()
sector_config = load_lines()
NUM_RINGS = len(ring_data)

clicked_points = []
canvas_size = None

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_points.append((x, y))
        ring_ids = classify_ring(x, y)
        sector_id = classify_sector(x, y)
        field = classify_field(ring_ids, sector_id)
        print(f"[Click] Point at ({x}, {y}) → {field}")

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

def main():
    global canvas_size
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        print("Failed to read from camera.")
        return

    canvas_size = (frame.shape[1], frame.shape[0])
    detector = DartDetector()
    print("Press 'q' to quit. Throw darts and watch for results...")

    def on_thresh_change(val):
        detector.motion_thresh = val

    cv2.namedWindow("Dartboard View")
    cv2.setMouseCallback("Dartboard View", mouse_callback)
    cv2.createTrackbar("Threshold", "Dartboard View", detector.motion_thresh, 100, on_thresh_change)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        virtual_canvas = draw_virtual_canvas()
        overlay = frame.copy()
        mask = virtual_canvas[:, :, 1] > 0
        overlay[mask] = virtual_canvas[mask]
        frame = overlay

        new_darts, thresh_img, boxes, motion_level = detector.update(frame)

        cv2.putText(frame, f"Motion Level: {motion_level:.0f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        for (x, y, w, h) in boxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "Blob", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 0, 255), 1)

        for (x, y) in clicked_points:
            cv2.circle(frame, (x, y), 6, (255, 0, 255), -1)

        for (x, y) in new_darts:
            ring_ids = classify_ring(int(x), int(y))
            sector_id = classify_sector(int(x), int(y))
            field = classify_field(ring_ids, sector_id)
            print(f"[Auto] Dart hit at ({x:.1f}, {y:.1f}) → {field}")

        for (x, y) in detector.known_darts:
            cv2.circle(frame, (int(x), int(y)), 6, (255, 0, 0), -1)

        thresh_display = cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGR) if thresh_img is not None else np.zeros_like(frame)
        thresh_display = cv2.resize(thresh_display, (frame.shape[1], frame.shape[0]))

        debug_merged = frame.copy()
        for group in detector.get_groups():
            cv2.drawContours(debug_merged, group, -1, (0, 255, 255), 2)

        debug_tip = cv2.imread("last_detected_dart.png", cv2.IMREAD_COLOR)
        debug_tip = cv2.resize(debug_tip, (debug_merged.shape[1],
                                           debug_merged.shape[0])) if debug_tip is not None else np.zeros_like(
            debug_merged)
        top_row = np.hstack((frame, thresh_display))
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
    cv2.destroyAllWindows()
    os.remove("last_detected_dart.png")

if __name__ == "__main__":
    main()