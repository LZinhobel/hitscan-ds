import cv2
import cv2.aruco as aruco
import os

def generate_marker(marker_id=0, size=300, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "markers")
    os.makedirs(output_dir, exist_ok=True)

    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size)

    filepath = os.path.join(output_dir, f"aruco_marker_{marker_id}.png")
    cv2.imwrite(filepath, marker_img)

    print(f"Marker with ID {marker_id} saved as {filepath}")

if __name__ == "__main__":
    for i in range(4):
        generate_marker(marker_id=i)