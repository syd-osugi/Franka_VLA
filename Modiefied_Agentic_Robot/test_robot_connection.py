#!/usr/bin/env python3
import numpy as np
import time
import os
import sys

try:
    from pylibfranka import Robot
except ImportError:
    print("[ERROR] 'pylibfranka' library is not installed.")
    print("Please install it using: pip install pylibfranka")
    sys.exit(1)

# --- CONFIGURATION ---
# Replace this with your Franka Robot's IP address
ROBOT_IP = "192.168.1.100" 

def main():
    # 1. Check for Root Permissions
    if os.geteuid() != 0:
        print("[ERROR] You are not running as root.")
        print("This script requires real-time permissions.")
        print("Please run with: sudo python3 test_robot_connection.py")
        sys.exit(1)

    print(f"[INFO] Attempting to connect to robot at {ROBOT_IP}...")
    
    robot = None
    try:
        # 2. Connect to Robot
        robot = Robot(ROBOT_IP)
        print("[SUCCESS] Connected to Robot!")
        
        # Set safe collision behavior
        robot.set_collision_behavior(
            [20.0]*7, [20.0]*7, [20.0]*6, [20.0]*6
        )
        
    except Exception as e:
        print(f"[FAILED] Could not connect. Error: {e}")
        print("Check if robot is powered on, PC is connected to robot network, and IP is correct.")
        sys.exit(1)

    print("\n[INFO] Reading current robot pose...")
    print("Move the robot manually (freedrive) to see if the numbers change.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            # 3. Read State
            state = robot.read_once()
            
            # 4. Extract Transformation Matrix (O_T_EE)
            # This is a flat list of 16 floats in Column-Major order
            pose_flat = state.O_T_EE
            
            # 5. Convert to 4x4 Matrix
            # Reshape using order='F' (Fortran/Column-Major) to get correct axes
            T = np.array(pose_flat).reshape((4, 4), order='F')
            
            # Extract Rotation (3x3) and Translation (3x1)
            R = T[:3, :3]
            t = T[:3, 3]
            
            # 6. Print Results
            print("-" * 60)
            print(f"Translation (x, y, z) [meters]:")
            print(f"  X: {t[0]:.4f}  Y: {t[1]:.4f}  Z: {t[2]:.4f}")
            
            print(f"Rotation Matrix (Row 1):")
            print(f"  {R[0, 0]:.3f}  {R[0, 1]:.3f}  {R[0, 2]:.3f}")
            
            # Optional: Print Joint Positions too
            # print(f"Joints: {np.round(state.q, 3)}")
            
            time.sleep(0.25) # Update 4 times a second
            
    except KeyboardInterrupt:
        print("\n[INFO] Test Stopped.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred during read: {e}")

if __name__ == "__main__":
    main()