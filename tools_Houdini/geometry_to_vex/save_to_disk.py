import hou

# Get the current node
current_node = hou.pwd()
print(f"Current node path: {current_node.path()}")

# Construct the path to the target node
target_path = "../rop_gltf7"
print(f"Target path: {target_path}")

try:
    # Get the node
    target_node = hou.node(target_path)
    if not target_node:
        raise ValueError(f"Node not found: {target_path}")
    
    # Check if the execute button exists
    execute_parm = target_node.parm("execute")
    if not execute_parm:
        raise ValueError(f"Execute button not found on node: {target_path}")
    
    print(f"Node found: {target_node.name()}")
    
    # Press the "Save to disk" button
    execute_parm.pressButton()
    
    print("Save to disk executed.")
    
except Exception as e:
    print(f"Error: {e}")
