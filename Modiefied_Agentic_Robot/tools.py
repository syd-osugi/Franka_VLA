# import base64
# import json
# import time
# from io import BytesIO

# import cv2
# import numpy as np
# import pyrealsense2 as rs
# from PIL import Image

# robot = "dummy robot"

# tool_json_list = [
#     {
#         "type": "function",
#         "function": {
#             "name": "get_webcam_frame",
#             "description": "Capture a single 1920x1080 frame from the webcam for visual analysis.",
#             "parameters": {"type": "object", "properties": {}, "required": []},
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "get_depth_frames",
#             "description": "Captures a 1280x720 RGB frame and aligned depth data. Use this to identify objects before calling get_xyz_coords.",
#             "parameters": {"type": "object", "properties": {}, "required": []},
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "get_xyz_coords",
#             "description": (
#                 "Convert pixel [u, v] coordinates (from a 1280x720 scale) into XYZ meters."
#                 "Uses standard image pixels where [0, 0] is the top left"
#                 "If a point returns 'invalid' (status: invalid), do not retry the same pixel. "
#                 "Instead, pick a new pixel 5-10 units away to bypass depth sensor noise."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "coords": {
#                         "type": "array",
#                         "description": "List of [x, y] pixel coordinates based on 1280x720 resolution.",
#                         "items": {
#                             "type": "array",
#                             "items": {"type": "integer"},
#                             "minItems": 2,
#                             "maxItems": 2,
#                         },
#                     }
#                 },
#                 "required": ["coords"],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "robot_control",
#             "description": (
#                 "Sends waypoints in XYZ meters. Only use coordinates obtained via get_xyz_coords. "
#                 "Never estimate coordinates or use raw pixel values here."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "waypoints": {
#                         "type": "array",
#                         "minItems": 1,
#                         "items": {
#                             "type": "object",
#                             "properties": {
#                                 "x": {"type": "number"},
#                                 "y": {"type": "number"},
#                                 "z": {"type": "number"},
#                             },
#                             "required": ["x", "y", "z"],
#                         },
#                     }
#                 },
#                 "required": ["waypoints"],
#             },
#         },
#     },
# ]


# def get_webcam_frame(webcam):
#     print("capturing image")
#     frame = webcam.get_frame()
#     frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#     frame = frame.convert("RGB")
#     # frame = frame.resize((640, 480))
#     buffer = BytesIO()
#     frame.save(buffer, format="JPEG", quality=85)
#     return base64.b64encode(buffer.getvalue()).decode("utf-8")


# def get_depth_frames(depthcam):
#     print("capturing depth images")
#     for _ in range(100):
#         rgb, depth, depth_rs = depthcam.get_frames()

#         # ADD THIS LINE TO SEE WHAT THE CAMERA IS RETURNING:
#         if _ == 0 or _ == 50: print(f"Attempt {_}: RGB={rgb is not None}, Depth={depth is not None}, RS={depth_rs is not None}")
        
#         if rgb is not None and depth is not None and depth_rs is not None:
#             break
#         time.sleep(0.01)
#     else:
#         raise RuntimeError("Timed out waiting for camera frames")

#     # Preserve the exact captured depth frame for later tool calls
#     depth_rs.keep()
#     depthcam.last_depth_rs = depth_rs

#     rgb_img = Image.fromarray(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
#     rgb_buffer = BytesIO()
#     rgb_img.save(rgb_buffer, format="JPEG", quality=85)
#     rgb_b64 = base64.b64encode(rgb_buffer.getvalue()).decode("utf-8")

#     depth_display = cv2.convertScaleAbs(depth, alpha=0.03)
#     depth_colormap = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)

#     depth_img = Image.fromarray(cv2.cvtColor(depth_colormap, cv2.COLOR_BGR2RGB))
#     depth_buffer = BytesIO()
#     depth_img.save(depth_buffer, format="JPEG", quality=85)
#     depth_b64 = base64.b64encode(depth_buffer.getvalue()).decode("utf-8")

#     xyz = depthcam.get_xyz_image()

#     depthcam.last_rgb = rgb.copy()

#     return rgb_b64, depth_b64, xyz, rgb, depth, depth_rs


# def get_xyz_coords(depthcam, coords, depth_rs):
#     if depth_rs is None:
#         return None

#     coords = np.asarray(coords, dtype=np.int32).reshape(-1, 2)

#     intrinsics = depth_rs.profile.as_video_stream_profile().intrinsics
#     h = depth_rs.get_height()
#     w = depth_rs.get_width()

#     out = []
#     for x, y in coords:
#         if not (0 <= x < w and 0 <= y < h):
#             out.append([np.nan, np.nan, np.nan])
#             continue

#         z = depth_rs.get_distance(x, y)
#         if z <= 0:
#             out.append([np.nan, np.nan, np.nan])
#             continue

#         xyz = rs.rs2_deproject_pixel_to_point(intrinsics, [float(x), float(y)], z)
#         out.append(xyz)

#     return np.asarray(out, dtype=np.float32)


# def robot_control(waypoints, robot):

#     for wp in waypoints:
#         if not all(k in wp for k in ("x", "y", "z")):
#             raise ValueError("Each waypoint must contain x, y, z.")
#         if any(abs(wp[k]) > 5 for k in ("x", "y", "z")):
#             raise ValueError("Waypoint values look invalid for meters.")

#     print("Sending commands to robot")
#     print(robot)
#     print(f"Waypoints: \n {waypoints}")

#     status = f"VIRTUAL MOVE: Robot would move through {len(waypoints)} points."
#     for i, wp in enumerate(waypoints):
#         status += (
#             f"\n Point {i + 1}: X={wp['x']:.3f}m, Y={wp['y']:.3f}m, Z={wp['z']:.3f}m"
#         )
#     print(status)
#     return status


# def dispatch(
#     tool_name: str, tool_args: dict, webcam, depthcam
# ) -> tuple[str, dict | None]:
#     """Returns (tool_result_string, optional_extra_message)"""
#     print(f"[DISPATCH] tool={tool_name} args={json.dumps(tool_args, indent=2)}")
#     print(f"Selected Tool: {tool_name}")

#     if tool_name == "get_depth_frames" and depthcam.last_depth_rs is not None:
#         return (
#             "Depth frame already captured. Use get_xyz_coords with the existing frame. "
#             "Do NOT call get_depth_frames again unless explicitly told to refresh.",
#             None,
#         )

#     elif tool_name == "get_xyz_coords":
#         coords = tool_args.get("coords", [])
#         if depthcam.last_depth_rs is None:
#             return "ERROR: No saved depth frame. Call get_depth_frames first.", None

#         if hasattr(depthcam, "last_rgb"):
#             debug_img = depthcam.last_rgb.copy()
#             for u, v in coords:
#                 cv2.drawMarker(debug_img, (u, v), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
#             cv2.imwrite("last_ai_aim.jpg", debug_img)
#             print("[DEBUG] Saved AI target visualization to last_ai_aim.jpg")

#         xyz = get_xyz_coords(depthcam, coords, depthcam.last_depth_rs)
#         points = xyz.tolist()

#         # Tell the agent explicitly which coords failed — don't silently return nan
#         results = []
#         for (u, v), pt in zip(coords, points):
#             if any(np.isnan(v) for v in pt):
#                 results.append({"pixel": [u, v], "status": "invalid", "xyz": None})
#             else:
#                 results.append({"pixel": [u, v], "status": "ok", "xyz": pt})

#         return json.dumps({"units": "meters", "points": results}), None

#     elif tool_name == "get_webcam_frame":
#         image = get_webcam_frame(webcam)
#         extra = {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "image_url",
#                     "image_url": {"url": f"data:image/jpeg;base64,{image}"},
#                 }
#             ],
#         }
#         return "Webcam frame captured successfully.", extra

#     elif tool_name == "get_depth_frames":
#         rgb_b64, depth_b64, xyz, rgb, depth, depth_rs = get_depth_frames(depthcam)

#         extra = {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "image_url",
#                     "image_url": {"url": f"data:image/jpeg;base64,{rgb_b64}"},
#                 },
#             ],
#         }

#         return "Depth frames captured successfully.", extra

#     elif tool_name == "robot_control":
#         waypoints = tool_args.get("waypoints", [])
#         success = robot_control(waypoints, robot)
#         return (
#             "Robot commands sent successfully." if success else "Robot control failed."
#         ), None

#     raise ValueError(f"Unknown tool: {tool_name}")

import base64
import json
import time
from io import BytesIO
import numpy as np

import cv2
import pyrealsense2 as rs
from PIL import Image

# Import our new transformer
import transforms_utils as tf

# --- ROBOT CONNECTION ---
# We use 'panda_py' which is a python wrapper for libfranka
# If you are using ROS, you would import your ROS node here instead.
try:
    import panda_py
    # Initialize the robot controller
    # Replace '192.168.1.100' with your robot's IP address
    robot = panda_py.Panda("10.31.82.199") 
except ImportError:
    print("[WARN] panda_py not installed. Robot control will be simulated.")
    robot = None
except Exception as e:
    print(f"[WARN] Could not connect to robot: {e}")
    robot = None

transformer = None

def init_transformer(table_height):
    """Initialize the transformer from main.py"""
    global transformer
    transformer = tf.RobotTransformer(table_height=table_height)

# --- ROBOT POSE FUNCTION ---
def get_robot_pose():
    """
    Gets the current End-Effector pose from the Franka Robot.
    Returns: Rotation Matrix (3x3), Translation Vector (3x1)
    """
    if robot is None:
        # Simulation Fallback
        return np.eye(3), np.array([0.5, 0.0, 0.3])

    try:
        # 1. Get the transformation matrix from libfranka/panda_py
        # This is usually the O_T_EE (Base to End-Effector) matrix
        # It returns a 4x4 matrix (or 16-element array)
        pose_matrix = robot.get_pose()
        
        # 2. Handle Data Format
        # libfranka returns a 4x4 matrix. 
        # IMPORTANT: libfranka often uses Column-Major ordering.
        # If the matrix looks transposed, numpy needs to read it correctly.
        # panda_py 'get_pose()' usually returns a 4x4 numpy array (Row-Major).
        
        R = pose_matrix[:3, :3]
        t = pose_matrix[:3, 3]
        
        return R, t
        
    except Exception as e:
        print(f"[ERROR] Failed to get robot pose: {e}")
        # Return safe fallback
        return np.eye(3), np.array([0.0, 0.0, 0.0])
# # ------------------------------
# # potentially needed since libfranka uses C++

# def get_robot_pose():
#     if robot is None:
#         return np.eye(3), np.array([0.5, 0.0, 0.3])

#     # Example if reading raw 'O_T_EE' array (16 floats)
#     # O_T_EE = robot.read_once().O_T_EE
    
#     # Convert flat array to 4x4 Matrix (Column-Major to Numpy Row-Major)
#     # T = np.array(O_T_EE).reshape(4, 4, order='F')
    
#     # If using panda_py, get_pose() handles this for you:
#     T = robot.get_pose()
    
#     R = T[:3, :3]
#     t = T[:3, 3]
#     return R, t
    # ------------------------------


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


def get_webcam_frame(webcam):
    print("capturing image")
    frame = webcam.get_frame()
    frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    frame = frame.convert("RGB")
    buffer = BytesIO()
    frame.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_depth_frames(depthcam):
    print("capturing depth images")
    # ... (Keep existing logic for capturing frames) ...
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
    return rgb_b64, "", None, rgb, depth, depth_rs # Returning empty depth img to save bandwidth if not needed


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

        # 1. Get Robot Pose
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
        success = robot_control(waypoints, robot)
        return "Robot commands sent.", None

    raise ValueError(f"Unknown tool: {tool_name}")

def robot_control(waypoints, robot):
    print("Sending commands to robot")
    print(f"Waypoints: \n {waypoints}")
    # TODO: Send to Franka
    return True