import base64
import json
import time
from io import BytesIO
import numpy as np
import cv2
import pyrealsense2 as rs
from PIL import Image

# Import our transformer utility
import src.transforms_utils as tf

# --- ROBOT CONNECTION (Using pylibfranka) ---
try:
    from pylibfranka import Robot
except ImportError:
    print("[ERROR] 'pylibfranka' not installed. Run: pip install pylibfranka")
    Robot = None

robot = None

def init_robot(ip="192.168.1.100"):
    """
    Connects to the Franka Robot.
    Call this once at the start of main.py
    """
    global robot
    if Robot is None:
        print("[WARN] Robot library not available.")
        return False
    
    try:
        print(f"[INFO] Connecting to robot at {ip}...")
        robot = Robot(ip)
        # Set safe collision behavior
        robot.set_collision_behavior(
            [20.0]*7, [20.0]*7, [20.0]*6, [20.0]*6
        )
        # Verify connection by reading once
        robot.read_once()
        print("[INFO] Robot connected successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to connect to robot: {e}")
        robot = None
        return False

def get_robot_pose():
    """
    Gets the current End-Effector pose from the Franka Robot.
    Returns: Rotation Matrix (3x3), Translation Vector (3x1)
    """
    global robot
    if robot is None:
        # Fallback for testing without robot
        # print("[WARN] Robot not connected. Returning dummy pose.")
        return np.eye(3), np.array([0.5, 0.0, 0.3])

    try:
        # 1. Read state
        state = robot.read_once()
        
        # 2. Get O_T_EE (Base to End-Effector)
        # This is a flat list of 16 floats in Column-Major order
        pose_flat = state.O_T_EE
        
        # 3. Convert to 4x4 Matrix
        # 'order=F' (Fortran) is critical here because libfranka is Column-Major
        T = np.array(pose_flat).reshape((4, 4), order='F')
        
        # 4. Extract R and t
        R = T[:3, :3]
        t = T[:3, 3]
        
        return R, t

    except Exception as e:
        print(f"[ERROR] Failed to get robot pose: {e}")
        return np.eye(3), np.array([0.0, 0.0, 0.0])

# --- TRANSFORMER INIT ---
transformer = None

def init_transformer(table_height):
    """Initialize the transformer from main.py"""
    global transformer
    transformer = tf.RobotTransformer(table_height=table_height)

# --- TOOL DEFINITIONS ---
tool_json_list = [
    {
        "type": "function",
        "function": {
            "name": "get_webcam_frame",
            "description": "Capture a single frame from the static webcam for visual analysis.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_depth_frames",
            "description": "Captures RGB frame and aligned depth data from the WRIST camera. Use this to identify objects close to the robot.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_webcam_xyz",
            "description": (
                "Convert pixel [u, v] from the STATIC WEBCAM (bird's eye) into Robot Base XYZ meters. "
                "Use this for objects seen in the webcam. Assumes objects are on the table."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coords": {
                        "type": "array",
                        "description": "List of [x, y] pixel coordinates based on webcam resolution.",
                        "items": {"type": "array", "items": {"type": "integer"}},
                    }
                },
                "required": ["coords"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_xyz_coords",
            "description": (
                "Convert pixel [u, v] from the WRIST CAMERA into Robot Base XYZ meters. "
                "Use this for objects seen in the wrist camera depth view."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coords": {
                        "type": "array",
                        "description": "List of [x, y] pixel coordinates.",
                        "items": {"type": "array", "items": {"type": "integer"}},
                    }
                },
                "required": ["coords"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "robot_control",
            "description": ("Sends waypoints in XYZ meters (Robot Base Frame)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"},
                            },
                            "required": ["x", "y", "z"],
                        },
                    }
                },
                "required": ["waypoints"],
            },
        },
    },
]

# --- HELPER FUNCTIONS ---

def get_webcam_frame(webcam):
    print("capturing image")
    frame = webcam.get_frame()
    if frame is None: return ""
    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    frame = frame.convert("RGB")
    buffer = BytesIO()
    frame.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def get_depth_frames(depthcam):
    print("capturing depth images")
    for _ in range(100):
        rgb, depth, depth_rs = depthcam.get_frames()
        if rgb is not None and depth is not None and depth_rs is not None:
            break
        time.sleep(0.01)
    else:
        raise RuntimeError("Timed out waiting for camera frames")

    depth_rs.keep()
    depthcam.last_depth_rs = depth_rs

    rgb_img = Image.fromarray(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
    rgb_buffer = BytesIO()
    rgb_img.save(rgb_buffer, format="JPEG", quality=85)
    rgb_b64 = base64.b64encode(rgb_buffer.getvalue()).decode("utf-8")

    depthcam.last_rgb = rgb.copy()
    return rgb_b64, "", None, rgb, depth, depth_rs

def robot_control(waypoints, robot_obj):
    print("Sending commands to robot")
    print(f"Waypoints: \n {waypoints}")
    
    # TODO: Implement real robot movement here if desired.
    # For now, it just returns a virtual status string.
    
    status = f"VIRTUAL MOVE: Robot would move through {len(waypoints)} points."
    for i, wp in enumerate(waypoints):
        status += f"\n Point {i + 1}: X={wp['x']:.3f}m, Y={wp['y']:.3f}m, Z={wp['z']:.3f}m"
    print(status)
    return status

# --- DISPATCHER ---

def dispatch(
    tool_name: str, tool_args: dict, webcam, depthcam
) -> tuple[str, dict | None]:
    """Returns (tool_result_string, optional_extra_message)"""
    print(f"[DISPATCH] tool={tool_name} args={json.dumps(tool_args, indent=2)}")

    if tool_name == "get_webcam_frame":
        image = get_webcam_frame(webcam)
        extra = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                }
            ],
        }
        return "Static webcam frame captured.", extra

    elif tool_name == "get_webcam_xyz":
        coords = tool_args.get("coords", [])
        if not transformer:
            return "ERROR: Transformer not initialized.", None
        
        results = []
        for u, v in coords:
            p_base = transformer.transform_webcam_to_base(u, v)
            if p_base is not None:
                results.append({"pixel": [u, v], "xyz_base": p_base.tolist()})
            else:
                results.append({"pixel": [u, v], "status": "calculation failed"})

        return json.dumps({"source": "static_webcam", "points": results}), None

    elif tool_name == "get_depth_frames":
        rgb_b64, _, _, rgb, depth, depth_rs = get_depth_frames(depthcam)
        extra = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{rgb_b64}"},
                },
            ],
        }
        return "Wrist depth frames captured.", extra

    elif tool_name == "get_xyz_coords":
        coords = tool_args.get("coords", [])
        if depthcam.last_depth_rs is None:
            return "ERROR: No saved depth frame. Call get_depth_frames first.", None
        
        if not transformer:
            return "ERROR: Transformer not initialized.", None

        # 1. Get Robot Pose (Using pylibfranka)
        R_ee, t_ee = get_robot_pose()

        intrinsics = depthcam.last_depth_rs.profile.as_video_stream_profile().intrinsics
        h = depthcam.last_depth_rs.get_height()
        w = depthcam.last_depth_rs.get_width()

        results = []
        for x, y in coords:
            if not (0 <= x < w and 0 <= y < h):
                results.append({"pixel": [x, y], "status": "out of bounds"})
                continue

            # 2. Get Depth and Deproject (Camera Frame)
            z = depthcam.last_depth_rs.get_distance(x, y)
            if z <= 0:
                results.append({"pixel": [x, y], "status": "invalid depth"})
                continue
            
            p_cam = np.array(rs.rs2_deproject_pixel_to_point(intrinsics, [float(x), float(y)], z))

            # 3. Transform to Base Frame
            p_base = transformer.transform_wrist_to_base(p_cam, R_ee, t_ee)
            
            if p_base is not None:
                results.append({"pixel": [x, y], "xyz_base": p_base.tolist()})
            else:
                results.append({"pixel": [x, y], "status": "transform failed"})

        return json.dumps({"source": "wrist_camera", "points": results}), None

    elif tool_name == "robot_control":
        waypoints = tool_args.get("waypoints", [])
        # We pass 'robot' global variable to the function
        success = robot_control(waypoints, robot)
        return "Robot commands sent.", None

    raise ValueError(f"Unknown tool: {tool_name}")