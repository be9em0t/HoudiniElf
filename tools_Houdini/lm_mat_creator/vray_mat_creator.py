# Create V-Ray MaterialBuilderNodes
# based on a provided template material

# // Prim wranlge to assign Landmark materials
# // Updates s@shop_materialpath to pint to the new material 
# string matnetPath = chs("Matnet_full_path");
# string oldMat = s@shop_materialpath;
# string parts[] = split(oldMat, "_");
# string result = parts[1] + "_" + parts[2] + "_" + parts[3];
# result = tolower(result);
# s@shop_materialpath = matnetPath + "/principled_" + result;
# s@shop_materialpath = matnetPath + "/vrM_" + result;

import hou
import os

# Start directory
start_directory = hou.getenv('HIP')
# Let the user pick one of the texture files (used to find the directory) or any image inside the folder
selection = hou.ui.selectFile(start_directory, title="Select a Folder (pick any texture in the folder)", collapse_sequences=True, file_type=hou.fileType.Image, chooser_mode=hou.fileChooserMode.Read)
# If the user cancelled the file chooser, selection can be empty or None — handle that gracefully
if not selection:
    hou.ui.displayMessage('No file or folder selected. Operation cancelled by user.')
    raise SystemExit('User cancelled file selection')
selection_expanded = hou.expandString(selection)
# print(selection)
# print(selection_expanded)


selected_extension = os.path.splitext(selection_expanded)[1]
selected_directory = os.path.dirname(selection_expanded)


all_files = os.listdir(selected_directory)
filenames = [f for f in all_files if os.path.splitext(f)[1] == selected_extension]
filenames.sort()
lenFilenames = len(filenames)
# print(filenames)

# Get the current context
network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
current_context = network_editor.pwd() if network_editor else None

if current_context:
    # Ask user to pick an existing V-Ray material node to use as template
    template_node = None
    # If the user already has a node selected, prefill the dialog with its path so they can copy it
    sel_nodes = hou.selectedNodes()
    prefill = sel_nodes[0].path() if sel_nodes else ""

    # Show an input dialog with the current selection prefilled. If the user cancels, abort gracefully.
    btn, chosen = hou.ui.readInput("Enter path to a template V-Ray material (leave empty to use current selection):", buttons=("OK", "Cancel"), initial_contents=prefill)
    if btn != 0:
        # Cancel pressed
        hou.ui.displayMessage('Template selection cancelled by user. Operation aborted.')
        raise SystemExit('User cancelled template selection')

    chosen = chosen.strip()
    if chosen:
        template_node = hou.node(chosen)

    # If no path given, fallback to the current node selection in the network editor
    if template_node is None:
        if sel_nodes:
            template_node = sel_nodes[0]
        else:
            hou.ui.displayMessage("No template node provided and no node selected. Aborting.")
    else:
        # Iterate textures and clone the template for each
        for texture in filenames:
            file = os.path.join(selected_directory, texture)
            base = os.path.splitext(texture)[0]
            # Build a safe name similar to prior script: vrM_<basename>
            new_name = f"vrM_{base}"

            # If a node with that name already exists in the template's parent, append a suffix
            parent = template_node.parent()
            unique_name = new_name
            idx = 1
            while parent.node(unique_name) is not None:
                idx += 1
                unique_name = f"{new_name}_{idx}"

            # Duplicate (copy) the template node
            new_node = template_node.copyTo(parent)
            new_node.setName(unique_name, unique_name=True)

            # First, look for V-Ray image nodes that expose the BitmapBuffer_file parm (common for VRayMetaImageFile)
            set_parm = None
            set_node = None
            nodes_to_check = [new_node] + list(new_node.allSubChildren())

            for node in nodes_to_check:
                parm = node.parm('BitmapBuffer_file')
                if parm is not None:
                    try:
                        parm.set(file)
                        set_parm = 'BitmapBuffer_file'
                        set_node = node
                        break
                    except Exception:
                        pass

            # Fallback: try a few other common parm names if BitmapBuffer_file wasn't found
            if set_parm is None:
                candidate_parms = ["imageFile", "tex0", "Tex0", "map", "diffuse_map", "diffuse_file"]
                for node in nodes_to_check:
                    for p in candidate_parms:
                        parm = node.parm(p)
                        if parm is not None:
                            try:
                                parm.set(file)
                                set_parm = p
                                set_node = node
                                break
                            except Exception:
                                pass
                    if set_parm is not None:
                        break

            if set_node is not None:
                print(f"Created V-Ray material: {new_node.path()} -> set parm: {set_parm} on node {set_node.path()} to {file}")
            else:
                print(f"Created V-Ray material: {new_node.path()} -> no image parm found to set for {file}")

        # Layout the nodes in the network editor for better visibility
        current_context.layoutChildren()
else:
    print("No current context found in the network editor.")


