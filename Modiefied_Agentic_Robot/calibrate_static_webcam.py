#!/usr/bin/env python3
import numpy as np
import cv2
import os
import sys
import time

# Import the utility we created earlier
from transforms_utils import save_calibration

# --- NEW: Import the working library ---
from pylibfranka import Robot

# --- CONFIGURATION ---
# Camera ID (try 0, 1, or 2 depending on your system)
CAMERA_ID = 1 

# CHECKERBOARD DIMENSIONS (INNER CORNERS!)
# Count the intersections of black squares.
# Example: If board has 7 squares across, enter 6.
CHECKERBOARD = (6, 9) 

# Size of one square in meters (Measure your printed board!)
SQUARE_SIZE = 0.024 

# Number of images to collect
INTRINSIC_IMAGES = 15
EXTRINSIC_POSES = 15

# --- ROBOT CONFIGURATION ---
ROBOT_IP = "192.168.1.100" # REPLACE WITH YOUR ROBOT'S IP (e.g., "10.31.82.199")
robot = None

def init_robot():
    """Connects to the robot using pylibfranka."""
    global robot
    try:
        print(f"[INFO] Connecting to Robot at {ROBOT_IP}...")
        robot = Robot(ROBOT_IP)
        
        # Set reasonable collision behavior
        robot.set_collision_behavior(
            [20.0]*7, [20.0]*7, [20.0]*6, [20.0]*6
        )
        print("[INFO] Robot Connected Successfully.")
    except Exception as e:
        print(f"[ERROR] Could not connect to robot: {e}")
        print("[WARN] Falling back to DUMMY mode.")
        robot = None

def get_robot_pose():
    """
    Gets the current End-Effector pose from the Franka Robot.
    Returns: Rotation Matrix (3x3), Translation Vector (3x1)
    """
    global robot
    
    if robot is None:
        print("[WARN] DUMMY ROBOT POSE RETURNED.")
        return np.eye(3), np.array([0.5, 0.0, 0.3])

    try:
        # 1. Read the current state once
        state = robot.read_once()
        
        # 2. Get the transformation matrix (Base to End-Effector)
        # O_T_EE is a flat list of 16 floats in Column-Major order
        pose_flat = state.O_T_EE
        
        # 3. Convert to 4x4 Numpy Matrix
        # libfranka uses Column-Major order. We reshape using order='F' (Fortran).
        T = np.array(pose_flat).reshape((4, 4), order='F')
        
        # 4. Extract Rotation and Translation
        R = T[:3, :3]
        t = T[:3, 3]
        
        return R, t
        
    except Exception as e:
        print(f"[ERROR] Failed to get robot pose: {e}")
        return np.eye(3), np.array([0.0, 0.0, 0.0])

def main():
    # Check for sudo (Real-time permissions required)
    if os.geteuid() != 0:
        print("[WARN] You are not running as root (sudo).")
        print("[WARN] If you get 'Operation not permitted' errors, run with: sudo python3 calibrate_static_webcam.py")
        print("-" * 60)

    # 1. Initialize Robot
    init_robot()

    # 2. Initialize Camera
    cap = cv2.VideoCapture(CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    # Turn off autofocus for consistency
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(cv2.CAP_PROP_FOCUS, 0) # Might need adjustment (0, 10, or 255)

    # ==========================================
    # PART 1: Intrinsic Calibration
    # ==========================================
    print(f"\n--- STEP 1: INTRINSIC CALIBRATION ---")
    print(f"Show the checkerboard to the camera from different angles/distances.")
    print(f"Press 's' to save image. Collect {INTRINSIC_IMAGES} images.")
    print("Press 'd' when done.\n")

    objpoints = [] # 3D points in real world space
    imgpoints = [] # 2D points in image plane
    
    objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
    objp = objp * SQUARE_SIZE

    saved_count = 0
    K, D = None, None

    # Robust detection flags
    detection_flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FILTER_QUADS

    while saved_count < INTRINSIC_IMAGES:
        ret, frame = cap.read()
        if not ret: continue
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret_find, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, flags=detection_flags)
        
        vis_frame = frame.copy()
        if ret_find:
            cv2.drawChessboardCorners(vis_frame, CHECKERBOARD, corners, ret_find)
            cv2.putText(vis_frame, "DETECTED", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(vis_frame, "Searching...", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.putText(vis_frame, f"Saved: {saved_count}/{INTRINSIC_IMAGES}", (20, 460), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow("Intrinsic Calibration", vis_frame)
        
        key = cv2.waitKey(1)
        if key == ord('s') and ret_find:
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), 
                                               (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            imgpoints.append(corners_refined)
            objpoints.append(objp)
            saved_count += 1
            print(f"Saved image {saved_count}")
            
        elif key == ord('d'):
            break

    print("\nCalculating Intrinsics...")
    if saved_count >= 5:
        ret_calib, K, D, _, _ = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
        print("Camera Matrix K:\n", K)
        print("Distortion D:\n", D.ravel())
    else:
        print("Not enough images.")
        cap.release()
        cv2.destroyAllWindows()
        return

    # ==========================================
    # PART 2: Extrinsic Calibration (Eye-to-Hand)
    # ==========================================
    print(f"\n--- STEP 2: EXTRINSIC CALIBRATION ---")
    print(f"ATTACH CHECKERBOARD TO ROBOT END-EFFECTOR.")
    print(f"Move robot to {EXTRINSIC_POSES} different poses.")
    print("Ensure the checkerboard is visible in the camera for each pose.")
    print("Press 's' to capture robot pose and image.\n")

    R_gripper2base_list = []
    t_gripper2base_list = []
    R_target2cam_list = []
    t_target2cam_list = []

    saved_count = 0
    while saved_count < EXTRINSIC_POSES:
        ret, frame = cap.read()
        if not ret: continue
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret_find, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, flags=detection_flags)

        vis_frame = frame.copy()
        if ret_find:
            cv2.drawChessboardCorners(vis_frame, CHECKERBOARD, corners, ret_find)
        
        cv2.imshow("Extrinsic Calibration", vis_frame)
        key = cv2.waitKey(1)

        if key == ord('s') and ret_find:
            # Get Robot Pose (Calls pylibfranka)
            R_ee, t_ee = get_robot_pose()
            
            # Get Checkerboard Pose relative to Camera
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), 
                                               (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            
            _, rvec, tvec = cv2.solvePnP(objp, corners_refined, K, D)
            R_target2cam, _ = cv2.Rodrigues(rvec)

            R_gripper2base_list.append(R_ee)
            t_gripper2base_list.append(t_ee)
            R_target2cam_list.append(R_target2cam)
            t_target2cam_list.append(tvec)
            
            saved_count += 1
            print(f"Captured Pose {saved_count}/{EXTRINSIC_POSES}")
        
        elif key == ord('q'):
            break

    # ==========================================
    # PART 3: Compute and Save
    # ==========================================
    print("\nCalculating Hand-Eye Calibration (Eye-to-Hand)...")
    
    try:
        R_cam2base, t_cam2base = cv2.calibrateRobotWorldHandEye(
            R_gripper2base_list, t_gripper2base_list,
            R_target2cam_list, t_target2cam_list
        )

        print("\nResult: Camera to Base Transform")
        print("Rotation:\n", R_cam2base)
        print("Translation:\n", t_cam2base)

        save_calibration("static_webcam_calib", R_cam2base, t_cam2base, K, D)

    except Exception as e:
        print(f"\n[ERROR] Calibration calculation failed: {e}")
        print("This usually happens if the robot did not move enough between poses.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()