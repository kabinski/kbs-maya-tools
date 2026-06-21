# -----------------------------------------------------------------------------
# Script: KBS_CleanupKit
# Date: 2026-06-21
# GitHub: https://github.com/kabinski/kbs-maya-tools
# Sketchfab: https://sketchfab.com/johnniewhiskey
#
# AI Assistance: Gemini 3.1 Pro
# -----------------------------------------------------------------------------
# Description:
#   A utility tool for cleaning up messy Maya scenes. 
#   - Cleans up unused namespaces.
#   - Deletes empty HumanIK (HIK) definitions.
#   - Merges duplicated materials (e.g., mat1, mat2 -> mat).
#   - Generates a flat 3D text label of the current file name.
#   - Quick access to Maya's Optimize Scene Size options.
# -----------------------------------------------------------------------------

import maya.cmds as cmds
import maya.mel as mel
import os
import re

class KBS_CleanupKit(object):
    def __init__(self):
        self.win_name = "kbsCleanupKitWin"
        self.build_ui()

    def build_ui(self):
        # Prevent multiple windows
        if cmds.window(self.win_name, exists=True):
            cmds.deleteUI(self.win_name)

        # Create Window
        cmds.window(self.win_name, title="KBS_CleanupKit", widthHeight=(340, 360), sizeable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=('both', 5))

        cmds.separator(style='none', height=5)

        # =====================================================================
        # SECTION 1: Cleanup etc.
        # =====================================================================
        cmds.frameLayout(label="Cleanup etc.", collapsable=True, collapse=False, 
                         marginHeight=8, marginWidth=8, font="boldLabelFont", bgc=(0.25, 0.25, 0.25))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(label="Cleanup Namespace", height=30, backgroundColor=(0.35, 0.35, 0.35),
                    annotation="Removes all custom namespaces from the scene and merges content to root.",
                    command=self.do_cleanup_namespace)
        
        cmds.button(label="Cleanup HIK", height=30, backgroundColor=(0.35, 0.35, 0.35),
                    annotation="Deletes HumanIK character definitions that have no joints assigned.",
                    command=self.do_cleanup_hik)
        
        cmds.setParent('..') # End Column
        cmds.setParent('..') # End FrameLayout

        # =====================================================================
        # SECTION 2: Cleanup Material
        # =====================================================================
        cmds.frameLayout(label="Cleanup Material", collapsable=True, collapse=False, 
                         marginHeight=8, marginWidth=8, font="boldLabelFont", bgc=(0.25, 0.25, 0.25))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(label="Cleanup Duplicate Material(s)", height=30, backgroundColor=(0.35, 0.35, 0.35),
                    annotation="Finds duplicated materials (e.g., mat1, mat2), reassigns the base material (mat), and deletes the duplicates.",
                    command=self.do_cleanup_duplicate_materials)
        
        cmds.setParent('..') # End Column
        cmds.setParent('..') # End FrameLayout

        # =====================================================================
        # SECTION 3: Create Label typeMesh
        # =====================================================================
        cmds.frameLayout(label="Create Label typeMesh", collapsable=True, collapse=False, 
                         marginHeight=8, marginWidth=8, font="boldLabelFont", bgc=(0.25, 0.25, 0.25))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.button(label="Create Label typeMesh from File Name", height=30, backgroundColor=(0.35, 0.35, 0.35),
                    annotation="Creates a flat 3D text label above the character containing the filename and total frame count.",
                    command=self.do_create_typemesh)

        cmds.setParent('..') # End Column
        cmds.setParent('..') # End FrameLayout

        # =====================================================================
        # SECTION 4: Optimize Scene Size
        # =====================================================================
        cmds.separator(style='none', height=2)
        cmds.button(label="Open [Optimize Scene Size] Window", height=35, backgroundColor=(0.35, 0.35, 0.35),
                    annotation="Opens Maya's native Optimize Scene Size option box.",
                    command=self.do_open_optimize_scene)

        # Show Window
        cmds.showWindow(self.win_name)

    # -------------------------------------------------------------------------
    # Execution Methods
    # -------------------------------------------------------------------------
    def do_cleanup_namespace(self, *args):
        # Default namespaces that should not be touched
        defaults = ['UI', 'shared']
        namespaces = cmds.namespaceInfo(lon=True, recurse=True) or []
        
        # Sort by length descending to delete child namespaces before parents
        namespaces = sorted([ns for ns in namespaces if ns not in defaults], key=len, reverse=True)
        
        cmds.undoInfo(openChunk=True)
        try:
            count = 0
            for ns in namespaces:
                try:
                    cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
                    count += 1
                except:
                    pass # Skip if locked or read-only
            print("--- KBS_CleanupKit: Cleaned up {} namespace(s) ---".format(count))
        except Exception as e:
            cmds.warning("Error cleaning namespaces: {}".format(str(e)))
        finally:
            cmds.undoInfo(closeChunk=True)

    def do_cleanup_hik(self, *args):
        # Find all HumanIK Character Nodes
        hik_nodes = cmds.ls(type="HIKCharacterNode") or []
        
        cmds.undoInfo(openChunk=True)
        try:
            count = 0
            for node in hik_nodes:
                # Check if there are any connections from type 'joint'
                conns = cmds.listConnections(node, type="joint")
                if not conns:
                    cmds.delete(node)
                    count += 1
            print("--- KBS_CleanupKit: Deleted {} empty HIK definition(s) ---".format(count))
        except Exception as e:
            cmds.warning("Error cleaning HIK: {}".format(str(e)))
        finally:
            cmds.undoInfo(closeChunk=True)

    def do_cleanup_duplicate_materials(self, *args):
        materials = cmds.ls(mat=True)
        # Exclude standard Maya default materials
        defaults = ['lambert1', 'particleCloud1', 'standardSurface1']
        materials = [m for m in materials if m not in defaults]
        
        cmds.undoInfo(openChunk=True)
        try:
            count = 0
            for mat in materials:
                # Use regex to find trailing digits (e.g., body_mat1 -> 1)
                match = re.search(r'(\d+)$', mat)
                if match:
                    digit_str = match.group(1)
                    base_mat = mat[:-len(digit_str)] # Strip the digits to get the base name
                    
                    if base_mat in materials:
                        # Find objects currently using the duplicate material
                        sgs = cmds.listConnections(mat, type='shadingEngine') or []
                        for sg in set(sgs):
                            members = cmds.sets(sg, query=True) or []
                            if members:
                                # Select the geometry and assign the base material using hyperShade
                                cmds.select(members, replace=True)
                                cmds.hyperShade(assign=base_mat)
                        
                        # Delete the duplicate material safely
                        cmds.delete(mat)
                        count += 1
                        
            cmds.select(clear=True)
            print("--- KBS_CleanupKit: Cleaned up {} duplicate material(s) ---".format(count))
        except Exception as e:
            cmds.warning("Error cleaning materials: {}".format(str(e)))
        finally:
            cmds.undoInfo(closeChunk=True)

    def do_create_typemesh(self, *args):
        # Ensure Type plugin is loaded
        if not cmds.pluginInfo("Type", query=True, loaded=True):
            try:
                cmds.loadPlugin("Type")
            except Exception:
                cmds.warning("KBS_CleanupKit: Could not load 'Type.mll' plugin.")
                return

        cmds.undoInfo(openChunk=True)
        try:
            # Delete old label if it exists to avoid clutter
            if cmds.objExists("Label_typeMesh"):
                cmds.delete("Label_typeMesh")

            # Extract filename and max frame
            filepath = cmds.file(query=True, sceneName=True)
            if filepath:
                filename = os.path.splitext(os.path.basename(filepath))[0]
            else:
                filename = "untitled"
                
            max_frame = int(cmds.playbackOptions(query=True, maxTime=True))

            # Format text and convert to Hexadecimal
            display_text = "{} {}f".format(filename, max_frame)
            hex_text = " ".join("{:02x}".format(ord(c)) for c in display_text)

            # Create polygon type
            cmds.select(clear=True)
            mel.eval("CreatePolygonType;")
            sel = cmds.ls(selection=True)

            if not sel:
                return

            type_transform = sel[0]
            
            # Find history nodes
            history = cmds.listHistory(type_transform) or []
            type_nodes = cmds.ls(history, type="type")
            extrude_nodes = cmds.ls(history, type="typeExtrude")
            
            if type_nodes:
                type_node = type_nodes[0]
                cmds.setAttr(type_node + ".textInput", hex_text, type="string") 
                cmds.setAttr(type_node + ".currentFont", "Arial Black", type="string")
                cmds.setAttr(type_node + ".fontSize", 12.0)
                
                # Center Alignment
                try:
                    cmds.setAttr(type_node + ".alignmentMode", 2) 
                except:
                    pass

            # Disable Extrusion
            if extrude_nodes:
                extrude_node = extrude_nodes[0]
                try:
                    cmds.setAttr(extrude_node + ".enableExtrusion", 0) 
                except:
                    pass

            # Translate up to Y=210
            cmds.setAttr(type_transform + ".tx", 0)
            cmds.setAttr(type_transform + ".ty", 210)
            cmds.setAttr(type_transform + ".tz", 0)

            # Rename to "Label_typeMesh"
            final_name = cmds.rename(type_transform, "Label_typeMesh")
            
            cmds.select(final_name, replace=True)
            print("--- KBS_CleanupKit: Created Label: {} ---".format(final_name))

        except Exception as e:
            cmds.error("Failed to create typeMesh: {}".format(str(e)))
        finally:
            cmds.undoInfo(closeChunk=True)

    def do_open_optimize_scene(self, *args):
        # Execute Maya's native MEL command to open the Optimize Scene options window
        mel.eval("OptimizeSceneOptions;")
        print("--- KBS_CleanupKit: Opened Optimize Scene Size Window ---")

# Run the UI
if __name__ == "__main__":
    KBS_CleanupKit()
