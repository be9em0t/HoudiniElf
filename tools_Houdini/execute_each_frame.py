import hou

# Get parameters from the node
active = hou.pwd().parm("active").eval()  # Check if the script is active
node_path = hou.pwd().parm("node_path").eval()  # Path to the GLTF exporter node
button_name = hou.pwd().parm("button_name").eval()  # Button name
start_frame = hou.pwd().parm("start_frame").eval()  # Start frame
end_frame = hou.pwd().parm("end_frame").eval()  # End frame
frame_step = hou.pwd().parm("frame_step").eval()  # Frame step

def save_to_disk(node_path, button_name, start_frame, end_frame, frame_step):
    """
    Automates the Save to Disk process for a node with a button.

    Parameters:
        node_path (str): The path to the node with the Save to Disk button.
        button_name (str): The internal name of the button parameter.
        start_frame (int): The start frame of the time interval.
        end_frame (int): The end frame of the time interval.
        frame_step (int): The interval for saving (e.g., every 2nd frame).
    """
    try:
        # Get the node
        node = hou.node(node_path)
        if not node:
            raise ValueError(f"Node not found: {node_path}")
        
        # Check if the button exists
        if not node.parm(button_name):
            raise ValueError(f"Button '{button_name}' not found on node: {node_path}")
        
        # Iterate through the specified frame range
        for frame in range(start_frame, end_frame + 1, frame_step):
            # Set the current frame
            hou.setFrame(frame)
            
            # Press the button
            node.parm(button_name).pressButton()
            
            print(f"Saved frame {frame} to disk using node '{node_path}'.")

        print("Save to Disk process completed successfully.")
    
    except Exception as e:
        print(f"Error: {e}")

# Check if the script is active
if active:
    save_to_disk(node_path, button_name, start_frame, end_frame, frame_step)
else:
    print("Script is inactive. Skipping execution.")