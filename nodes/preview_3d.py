"""JS3D_Preview3D — preview-only output node for 3D models."""

import os
import json


class JS3D_Preview3D:
    """Preview a 3D model downstream in a workflow (output node, no data outputs)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh_path": ("STRING", {
                    "default": "",
                    "tooltip": "Path to a 3D model file",
                }),
            },
            "optional": {
                "camera_info": ("STRING", {
                    "default": "{}",
                    "tooltip": "Camera JSON from CameraRig node",
                }),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    CATEGORY = "3d"
    OUTPUT_NODE = True
    DESCRIPTION = "Preview a 3D model with interactive controls (output node)."

    def execute(self, mesh_path, camera_info="{}"):
        result = {
            "mesh_path": mesh_path,
            "camera_info": camera_info,
        }
        return {"ui": {"js3d_preview": [json.dumps(result)]}}


NODE_CLASS_MAPPINGS = {
    "JS3D_Preview3D": JS3D_Preview3D,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JS3D_Preview3D": "Preview 3D",
}
