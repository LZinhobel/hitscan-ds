import cv2
from file_handler import *
from draw_canvas import draw_ellipses, draw_sector_lines

NUM_RINGS = 6
canvas_size = None

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

def draw_virtual_canvas(show_lines=False):
    canvas = np.zeros((canvas_size[1], canvas_size[0], 3), dtype=np.uint8)
    draw_ellipses(canvas, rings[:current_ring + 1], current_ring=current_ring)

    if show_lines:
        draw_sector_lines(canvas, rings[0], line_rotation, line_offset_x, line_offset_y,
                          line_scale, line_stretch_x, line_stretch_y)

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
            scale_factors = [1.0, 0.85, 0.6, 0.5, 0.15, 0.06]
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
    global current_ring, auto_generated, mode, line_stretch_y, line_stretch_x
    global line_offset_x, line_offset_y, line_rotation, line_scale, rings, rings_loaded, canvas_size

    cam_index = select_camera()
    if cam_index is None:
        return

    cap = cv2.VideoCapture(cam_index)
    ret, frame = cap.read()
    if not ret:
        print("Failed to read from camera.")
        return

    canvas_size = (frame.shape[1], frame.shape[0])

    rings, rings_loaded = load_rings()
    line_rotation, line_offset_x, line_offset_y, line_scale, line_stretch_x, line_stretch_y = load_lines()

    if not rings_loaded:
        center_x = canvas_size[0] // 2
        center_y = canvas_size[1] // 2
        rings = [np.array([center_x, center_y, 100, 1.0, 1.0], dtype=np.float32)] + [np.zeros(5, dtype=np.float32) for _ in range(NUM_RINGS - 1)]
        print("Starting ring placed in canvas center.")

    print_controls()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        virtual_canvas = draw_virtual_canvas(show_lines=(mode == "lines"))
        canvas_h, canvas_w = virtual_canvas.shape[:2]
        frame_h, frame_w = frame.shape[:2]

        y_offset = (frame_h - canvas_h) // 2
        x_offset = (frame_w - canvas_w) // 2

        y_start = max(y_offset, 0)
        x_start = max(x_offset, 0)
        y_end = min(y_start + canvas_h, frame_h)
        x_end = min(x_start + canvas_w, frame_w)

        canvas_y_start = y_start - y_offset
        canvas_x_start = x_start - x_offset
        canvas_y_end = canvas_y_start + (y_end - y_start)
        canvas_x_end = canvas_x_start + (x_end - x_start)

        roi = frame[y_start:y_end, x_start:x_end]
        virtual_canvas_roi = virtual_canvas[canvas_y_start:canvas_y_end, canvas_x_start:canvas_x_end]
        mask = virtual_canvas_roi[:, :, 1] > 0

        roi[mask] = virtual_canvas_roi[mask]
        frame[y_start:y_end, x_start:x_end] = roi

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
