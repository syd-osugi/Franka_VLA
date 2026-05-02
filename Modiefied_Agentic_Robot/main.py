import src.depth_camera as depthcam
import src.LLM_interface as llm
import src.tools as tools
import src.webcam_capture as webcam
import time

def main():
    print("[SYSTEM] Initializing...")
    
    # 1. Initialize Transformer
    # Set your table height here (Z-coordinate in robot base frame)
    tools.init_transformer(table_height=0.1) 

    # 2. Initialize Interface and Cameras
    interface = llm.LLMinterface("models/Qwen3.5-4B-Q4_K_M.gguf", tools.tool_json_list)
    
    # Static Webcam (Bird's Eye)
    cam = webcam.Webcam(6, (640, 480)) 
    
    # Wrist Camera (RealSense D405)
    depth_cam = depthcam.RealSense(resolution=(640, 480), fps=15)

    print("[SYSTEM] System Ready. Waiting for commands...")

    try:
        while True:
            interface.get_text() # Get user input
            
            # Process with LLM
            # This automatically calls tools (get_xyz, robot_control, etc.)
            interface.send_message_with_tools(cam, depth_cam)
            
            interface.print_message()
            
            # Clean up history to save tokens
            interface.prune_image_history()
            
    except KeyboardInterrupt:
        print("\n[SYSTEM] Keyboard Interrupt.")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        print("exiting")
        depth_cam.stop()
        cam.stop_webcam()
        
        # Safety: Stop the robot if necessary
        if tools.robot is not None:
            try:
                # tools.robot.stop() # Optional: Stop control loop
                pass 
            except:
                pass
        
        print("done")

if __name__ == "__main__":
    main()