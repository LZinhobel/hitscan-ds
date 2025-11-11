import cv2
import numpy as np

def draw_ellipses(canvas, rings, current_ring=None):
    for i, ring in enumerate(rings):
        if current_ring is not None:
            color = (0, 255, 0) if i == current_ring else (255, 255, 255)
        else:
            color = (0, 255, 0)
        center = tuple(ring[0:2].astype(int))
        axes = (int(ring[2] * ring[3]), int(ring[2] * ring[4]))
        cv2.ellipse(canvas, center, axes, 0, 0, 360, color, 2)

def draw_sector_lines(canvas, outer_ring, rotation_deg, offset_x, offset_y, scale, stretch_x, stretch_y):
    cx, cy = outer_ring[0:2]
    radius = outer_ring[2] * max(outer_ring[3], outer_ring[4])
    for i in range(20):
        angle = np.deg2rad(i * 18 + rotation_deg)

        scaled_cos = np.cos(angle) * outer_ring[3] * scale * stretch_x
        scaled_sin = np.sin(angle) * outer_ring[4] * scale * stretch_y

        x = int(cx + radius * scaled_cos + offset_x)
        y = int(cy + radius * scaled_sin + offset_y)

        start_point = (int(cx) + int(offset_x), int(cy) + int(offset_y))
        color = (255, 0, 0) if i == 0 else (100, 100, 255)
        cv2.line(canvas, start_point, (x, y), color, 1)
