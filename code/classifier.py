import json
import cv2
import numpy as np
import math

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

def draw_map(highlight_rings=None, highlight_sector=None):
    img = np.zeros((canvas_size[1], canvas_size[0], 3), dtype=np.uint8)

    # Draw rings
    for i, ring in enumerate(ring_data):
        cx, cy = ring['cx'], ring['cy']
        axes = (int(ring['scale'] * ring['stretch_x']), int(ring['scale'] * ring['stretch_y']))
        color = (0, 0, 255) if highlight_rings and i in highlight_rings else (200, 200, 200)
        cv2.ellipse(img, (int(cx), int(cy)), axes, 0, 0, 360, color, 2)

    # Use outer_ring center + sector_config offsets for center
    outer_ring = ring_data[0]
    cx = outer_ring['cx'] + sector_config['offset_x']
    cy = outer_ring['cy'] + sector_config['offset_y']

    # Remove scaling logic for length — use the outer ring's ellipse axes directly
    # We'll draw the lines using axes lengths from the outer ring *without any extra scaling*

    axes_x = int(outer_ring['scale'] * outer_ring['stretch_x'])
    axes_y = int(outer_ring['scale'] * outer_ring['stretch_y'])

    # Adjust rotation offset so first line is between 20 and 1 at top (-9 degrees offset)
    rotation_offset = ((sector_config['rotation']) + 360) % 360 - 108

    for i in range(NUM_SECTORS):
        angle_deg = i * (360 / NUM_SECTORS) + rotation_offset
        angle_rad = math.radians(angle_deg)

        dx = math.cos(angle_rad) * axes_x
        dy = math.sin(angle_rad) * axes_y

        pt1 = (int(cx), int(cy))
        pt2 = (int(cx + dx), int(cy + dy))

        if i == 0:
            color = (255, 0, 0)  # first line between 20 and 1
            thickness = 2
        elif highlight_sector == i:
            color = (0, 255, 0)
            thickness = 2
        else:
            color = (100, 100, 255)
            thickness = 1

        cv2.line(img, pt1, pt2, color, thickness)

        # Optional: draw segment numbers
        label = str(DARTBOARD_NUMBERS[i])
        text_angle = math.radians(angle_deg + 9)
        text_radius = max(axes_x, axes_y) * 1.05
        tx = int(cx + math.cos(text_angle) * text_radius)
        ty = int(cy + math.sin(text_angle) * text_radius)
        cv2.putText(img, label, (tx - 10, ty + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    return img

def point_in_ellipse(x, y, ring):
    dx = x - ring['cx']
    dy = y - ring['cy']
    nx = dx / (ring['scale'] * ring['stretch_x'])
    ny = dy / (ring['scale'] * ring['stretch_y'])
    return nx**2 + ny**2 <= 1

def classify_ring(x, y):
    for i in range(NUM_RINGS - 1):
        outer = ring_data[i]
        inner = ring_data[i + 1]
        if point_in_ellipse(x, y, outer) and not point_in_ellipse(x, y, inner):
            return [i, i + 1]
    if point_in_ellipse(x, y, ring_data[-1]):
        return [NUM_RINGS - 1]
    return [0]

def classify_sector(x, y):
    outer_ring = ring_data[0]
    cx = outer_ring['cx'] + sector_config['offset_x']
    cy = outer_ring['cy'] + sector_config['offset_y']
    dx = x - cx
    dy = y - cy
    angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360

    # adjust so 0° is top center (between 20 and 1)
    angle = (angle - (sector_config['rotation']) + 360) % 360 + 108
    if angle > 360:
        angle -= 360
    sector_index = int(angle // (360 / NUM_SECTORS))
    return sector_index


def classify_field(ring_ids, sector_id):
    # If click is outside the outermost ring (ring 0), return 0 (outside)
    if 0 in ring_ids and len(ring_ids) == 1:
        return "0 (outside)"

    # Bullseye (innermost ring only)
    if len(ring_ids) == 1 and ring_ids[0] == 5:
        return "bullseye"

    # Unpack rings (outer and inner)
    outer, inner = (ring_ids[0], ring_ids[1]) if len(ring_ids) == 2 else (ring_ids[0], None)
    number = DARTBOARD_NUMBERS[sector_id]

    # Map ring pairs to dartboard zones
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
    else:
        # fallback for other rings (like if inside outer ring only)
        return f"single {number}"


def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        ring_ids = classify_ring(x, y)
        sector_id = classify_sector(x, y)
        field = classify_field(ring_ids, sector_id)
        print(f"Click at ({x},{y}) → {field}")
        disp = draw_map(highlight_rings=ring_ids, highlight_sector=sector_id)
        cv2.imshow("Dartboard Classifier", disp)


cv2.namedWindow("Dartboard Classifier")
cv2.setMouseCallback("Dartboard Classifier", on_mouse)
cv2.imshow("Dartboard Classifier", draw_map())

print("Click to classify. Press 'q' to quit.")
while True:
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break
cv2.destroyAllWindows()
