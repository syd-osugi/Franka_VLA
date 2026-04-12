import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import matplotlib.pyplot as plt

# Load desired model
# Using prompt-based model for better accuracy in detecting specific classes (e.g., person)
# Uncomment lines below to use yoloe-26l-seg
# ================================
model = YOLO("yoloe-26l-seg.pt")
# Add prompt to only detect the certain items
model.set_classes(["mouse"])
# ================================

# Use yolo26n-seg for faster inference, but it may be less accurate and will detect all classes
# Uncomment line below to use yolo26n-seg
# ================================
# model = YOLO("yolo26n-seg.pt")
# ================================

# Initalize the webcam
#cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()

# Get device product line for setting a supporting resolution
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
device_product_line = str(device.get_info(rs.camera_info.product_line))

# found_rgb = False
# for s in device.sensors:
#     if s.get_info(rs.camera_info.name) == 'RGB Camera':
#         found_rgb = True
#         break
# if not found_rgb:
#     print("The demo requires Depth camera with Color sensor")
#     exit(0)

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
pipeline.start(config)

# 3. Create Alignment Object
# rs.align allows us to align depth frames to other frames
align_to = rs.stream.color
align = rs.align(align_to)

try:
    while True:
        # Wait for coherent pairs
        # get frameset
        frames = pipeline.wait_for_frames()
        # process alignment
        aligned_frames = align.process(frames)
        #get aligned frames
        aligned_depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        
        if not aligned_depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(aligned_depth_frame.get_data())
        # Update color and depth frames:
        aligned_color_frame = np.asanyarray(aligned_frames.get_color_frame().get_data())

        #results_color = model(color_image)
        results_color = model(aligned_color_frame)

        
        # Display the results on the frame
        annotated_color_frame = results_color[0].plot()
        print(results_color[0])

        #get coordinate of center of bounding box
        xmin, ymin, xmax, ymax = results_color

        # Calculate center
        box_center_x = int((xmin + xmax) / 2)
        box_center_y = int((ymin + ymax) / 2)

        print(f"Center Pixel: ({box_center_x}, {box_center_y})")

        # Display the annotated frame
        #cv2.imshow('Webcam Object Segmentation', annotated_frame)

        # Display
        # cv2 does not work with depth image 
        cv2.imshow('D405 Stream', annotated_color_frame)
        
        # Convert depth to 8-bit per pixel (0-255) and apply colormap
        # depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        
        # images = np.hstack((aligned_color_frame, depth_colormap))
        # plt.imshow(images)

        if cv2.waitKey(1) == ord('q'):
            break
finally:
    pipeline.stop()
    cv2.destroyAllWindows()