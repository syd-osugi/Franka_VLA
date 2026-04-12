import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO

# Load desired model
# Using prompt-based model for better accuracy in detecting specific classes (e.g., person)
# Uncomment lines below to use yoloe-26l-seg
# ================================
model = YOLO("yoloe-26l-seg.pt")
# Add prompt to only detect the certain items
model.set_classes(["person", "mouse", "keyboard", "guitar"])
# ================================

# Use yolo26n-seg for faster inference, but it may be less accurate and will detect all classes
# Uncomment line below to use yolo26n-seg
# ================================
# model = YOLO("yolo26n-seg.pt")
# ================================

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
pipeline.start(config)

try:
    while True:
        # Wait for coherent pairs
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())
        
        # Predict on the image
        # YOLO Model does not work with depth image 
        results_color = model(color_image)
        
        # Display the results on the frame
        annotated_color_frame = results_color[0].plot()

        # Display
        cv2.imshow('D405 Stream', annotated_color_frame)
        if cv2.waitKey(1) == ord('q'):
            break
finally:
    pipeline.stop()
    cv2.destroyAllWindows()