from ultralytics import YOLO
import cv2
import torch
import numpy as np
from pathlib import Path

# Load a model. Current model is nano segmentation.
model = YOLO("yoloe-26l-seg.pt")
# Add prompt to only detect the certain items
model.set_classes(["cup"])

# Get the directory of the current script
script_dir = Path(__file__).resolve().parent
print(script_dir)
# Construct the path to your file
file_path = "Example_Images/Cup_Example.jpg"
print(file_path)

# Predict on provided cup image
results = model(file_path)

for r in results:
    boxes = r.boxes
    for box in boxes:
        # Get coordinates in different formats:
        b_xyxy = box.xyxy[0]  # [xmin, ymin, xmax, ymax] in pixels
        b_xywh = box.xywh[0]  # [x_center, y_center, width, height] in pixels
        b_norm = box.xywhn[0] # Normalized [0, 1] coordinates (standard YOLO format)

# Convert tensor to integer
b_x_center = int(b_xywh[0].item())
b_y_center = int(b_xywh[1].item())

for r in results:
    # This allows you to specify any valid system path and filename
    r.save(filename="cup_result.jpg")

image = cv2.imread("cup_result.jpg")
# Locate the center of the bounding box with a red circle
cv2.circle(image, (b_x_center, b_y_center), radius=5, color=(0, 0, 255), thickness=-1)
cv2.imwrite('center_bounding_box_cup_result.jpg', image)

print("yay")