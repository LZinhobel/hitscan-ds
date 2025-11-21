import math
from file_handler import load_rings, load_lines

Y_OFFSET = -65

ring_data, _ = load_rings()
print(ring_data)
sector_config = load_lines()
print(sector_config)

for ring in ring_data:
    ring[1] -= Y_OFFSET

new_sectors = []
for sector in sector_config:
    # Only process tuples or lists with enough coordinates
    if isinstance(sector, (tuple, list)) and len(sector) >= 4:
        # Some may include stretch_x and stretch_y, some not
        if len(sector) == 6:
            x1, y1, x2, y2, sx, sy = sector
            new_sectors.append((x1, y1 - Y_OFFSET, x2, y2 - Y_OFFSET, sx, sy))
        elif len(sector) == 4:
            x1, y1, x2, y2 = sector
            new_sectors.append((x1, y1 - Y_OFFSET, x2, y2 - Y_OFFSET))
        else:
            # Unexpected but valid format → copy unchanged
            new_sectors.append(sector)
    else:
        # Not a tuple/list → leave as-is
        new_sectors.append(sector)

sector_config = new_sectors

NUM_SECTORS = 20
DARTBOARD_NUMBERS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17,
                     3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

NUM_RINGS = len(ring_data)

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
    dx = x - ring[0]
    dy = y - ring[1]
    nx = dx / (ring[2] * ring[3])
    ny = dy / (ring[2] * ring[4])
    return nx ** 2 + ny ** 2 <= 1

def classify_sector(x, y):
    cx, cy = ring_data[0][0], ring_data[0][1]
    dx = x - cx
    dy = y - cy

    dart_angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360

    offset = (sector_config[0] - 100) % 360
    adjusted_angle = (dart_angle - offset + 360) % 360

    sector_angle_size = 360 / NUM_SECTORS

    sector_index = int(adjusted_angle // sector_angle_size)

    return sector_index


def classify_field(ring_ids, sector_id):
    if 0 in ring_ids and len(ring_ids) == 1:
        return "0"
    if len(ring_ids) == 1 and ring_ids[0] == 5:
        return "50"

    outer, inner = (ring_ids[0], ring_ids[1]) if len(ring_ids) == 2 else (ring_ids[0], None)
    number = DARTBOARD_NUMBERS[sector_id]

    # return detailed field description
    # if outer == 0 and inner == 1:
    #     return f"double {number}"
    # elif outer == 1 and inner == 2:
    #     return f"single {number} (outer)"
    # elif outer == 2 and inner == 3:
    #     return f"triple {number}"
    # elif outer == 3 and inner == 4:
    #     return f"single {number} (inner)"
    # elif outer == 4 and inner == 5:
    #     return f"outer bull"
    # return f"single {number}"

    if outer == 0 and inner == 1:
        return f"D{number}"
    elif outer == 1 and inner == 2:
        return f"S{number}"
    elif outer == 2 and inner == 3:
        return f"T{number}"
    elif outer == 3 and inner == 4:
        return f"S{number}"
    elif outer == 4 and inner == 5:
        return "25"
    return f"{number}"
