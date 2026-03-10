"""JS3D_CameraRig — define camera position and parameters."""

import json


class JS3D_CameraRig:
    """Define camera position and parameters for consistent 3D rendering."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "camera_type": (["perspective", "orthographic"],),
                "fov": ("FLOAT", {"default": 50.0, "min": 1.0, "max": 120.0, "step": 0.5}),
                "pos_x": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "pos_y": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "pos_z": ("FLOAT", {"default": 3.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "target_x": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "target_y": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "target_z": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "zoom": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 50.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("camera_info",)
    FUNCTION = "execute"
    CATEGORY = "3d"
    DESCRIPTION = "Define camera position and parameters for 3D rendering."

    def execute(self, camera_type, fov, pos_x, pos_y, pos_z,
                target_x, target_y, target_z, zoom):
        camera_info = {
            "cameraType": camera_type,
            "fov": fov,
            "position": {"x": pos_x, "y": pos_y, "z": pos_z},
            "target": {"x": target_x, "y": target_y, "z": target_z},
            "zoom": zoom,
        }
        return (json.dumps(camera_info),)


NODE_CLASS_MAPPINGS = {
    "JS3D_CameraRig": JS3D_CameraRig,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JS3D_CameraRig": "Camera Rig 3D",
}
