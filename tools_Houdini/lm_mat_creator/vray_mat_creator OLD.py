# Import the hou module
import hou

# # test read paramater
# node = hou.node('/mat/vrM_LM_Texture_switch_TEMP_id9/multiIdTex_Color')
# parm = node.parm('mode')
# parmVal = parm.eval()
# print(parmVal)

# Import the os module
import os

start_directory = hou.getenv('HIP')
selection = hou.ui.selectFile(start_directory, title="Select a Folder", collapse_sequences=True, file_type=hou.fileType.Image, chooser_mode=hou.fileChooserMode.Read)
selection_expanded = hou.expandString(selection)
# print(selection)
# print(selection_expanded)


selected_extension = os.path.splitext(selection_expanded)[1]
selected_directory = os.path.dirname(selection_expanded)


all_files = os.listdir(selected_directory)
filenames = [f for f in all_files if os.path.splitext(f)[1] == selected_extension]
filenames.sort()
lenFilenames = len(filenames)

# new vray material builder
parent_context = hou.node('/mat')
vrmBuilder_node = parent_context.createNode('vray_vop_builder', 'vrM_LM_TextureMat')

# Set material, matID and output
Material_node_name = '/mat/' + str(vrmBuilder_node) + '/vrayMtl'
Material_node = hou.node(Material_node_name)
Output_node_name = '/mat/' + str(vrmBuilder_node) + '/vrayOutput'
Output_node = hou.node(Output_node_name)
MaterialID_node = vrmBuilder_node.createNode('VRayNodeMtlMaterialID', 'ID01')

Material_node.setPosition([0,0])
MaterialID_node.setPosition([3,-1])
Output_node.setPosition([6,0])
MaterialID_node.setInput(0, Material_node)
Output_node.setInput(0, MaterialID_node)
MaterialID_node.parm('material_id_number').setExpression('substr($OS, 2, 3)')

# set multiTexture
TexMulti_Color_node = vrmBuilder_node.createNode('VRayNodeTexMulti', 'TexMulti_Color')
TexMulti_Alpha_node = vrmBuilder_node.createNode('VRayNodeTexMulti', 'TexMulti_Alpha')
UserInteger_node = vrmBuilder_node.createNode('VRayNodeTexUserInteger', 'UserInteger_TextureID')

UserInteger_node.setPosition([-6,3])
TexMulti_Color_node.setPosition([-5,1])
TexMulti_Alpha_node.setPosition([-5,-3])
TexMulti_Color_node.parm('mode').set('30')
TexMulti_Alpha_node.parm('mode').set('30')
TexMulti_Color_node.parm('tex_count').set(lenFilenames)
TexMulti_Alpha_node.parm('tex_count').set(lenFilenames)
UserInteger_node.parm('user_attribute').set('switch')
TexMulti_Color_node.setInput(0, UserInteger_node)
TexMulti_Alpha_node.setInput(0, UserInteger_node)
Material_node.setInput(0, TexMulti_Color_node)
Material_node.setInput(2, TexMulti_Alpha_node)
# tex_count


for index in range(0, lenFilenames):  # for numbers 1 to xx
    texIndex = index+1
    file = os.path.join(selected_directory, filenames[index])

    # parts = filenames[index].split("_")
    lm_id = int(filenames[index][8:11])
    print("Filename: {} | index: {}".format(filenames[index], lm_id) )

    TexMulti_Color_parmTexId = f'tex{texIndex}id' #this should be the LMID number
    TexMulti_Color_node.parm(TexMulti_Color_parmTexId).set(lm_id)
    TexMulti_Alpha_node.parm(TexMulti_Color_parmTexId).set(lm_id)
    TexMulti_inputName = f'tex_{texIndex}'
    imageNodeName = f'ImageFile{texIndex}_node'  
    # imageNode_parmName = f'ImageFile{texIndex}'  
    imageNode = vrmBuilder_node.createNode('VRayNodeMetaImageFile', imageNodeName)
    imageNode.setPosition([-12+index,index*-1])
    imageNode.parm('BitmapBuffer_file').set(file)
    # TexMulti_Color_node.setNamedInput('color', imageNode, TexMulti_Color_parmTexId)
    TexMulti_Color_node.setNamedInput(TexMulti_inputName, imageNode, 'color')
    TexMulti_Alpha_node.setNamedInput(TexMulti_inputName, imageNode, 'alpha')

# Don't forget to cook the node to apply the changes
Output_node.cook()

