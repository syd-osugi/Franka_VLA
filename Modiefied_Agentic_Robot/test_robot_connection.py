import numpy as np
import time

try:
    import panda_py
except ImportError:
    print("[ERROR] 'panda-py' library is not installed.")
    print("Please install it using: pip install panda-py")
    exit()

# --- CONFIGURATION ---
# Replace this with your Franka Robot's IP address
ROBOT_IP = "10.31.82.199" 

def main():
    print(f"[INFO] Attempting to connect to robot at {ROBOT_IP}...")
    
    try:
        # 1. Connect to Robot
        robot = panda_py.Panda(ROBOT_IP)
        print("[SUCCESS] Connected to Robot!")
        
    except Exception as e:
        print(f"[FAILED] Could not connect. Error: {e}")
        print("Check if robot is powered on, PC is connected to robot network, and IP is correct.")
        return

    print("\n[INFO] Reading current robot pose...")
    print("Move the robot manually to see if the numbers change.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            # 2. Get Pose
            pose_matrix = robot.get_pose()
            
            # 3. Extract Rotation and Translation
            R = pose_matrix[:3, :3]
            t = pose_matrix[:3, 3]
            
            # 4. Print Results
            print("-" * 40)
            print(f"Translation (x, y, z): {t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f}")
            # Print just the top row of rotation for brevity
            print(f"Rotation Row 1:        {R[0, 0]:.3f}, {R[0, 1]:.3f}, {R[0, 2]:.3f}")
            
            time.sleep(0.5) # Update every 0.5 seconds
            
    except KeyboardInterrupt:
        print("\n[INFO] Test Stopped.")

if __name__ == "__main__":
    main()