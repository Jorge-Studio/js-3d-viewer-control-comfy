"""JS3D_Load3DController — load 3D files with interactive viewer."""

import os
import json
import base64
import hashlib
import numpy as np
import torch
from pathlib import Path

import folder_paths

SUPPORTED_EXTENSIONS = {".ply", ".glb", ".gltf", ".obj", ".fbx", ".stl", ".splat"}


def _list_3d_files():
    input_dir = os.path.join(folder_paths.get_input_directory(), "3d")
    os.makedirs(input_dir, exist_ok=True)
    base = Path(folder_paths.get_input_directory())
    files = []
    for p in Path(input_dir).rglob("*"):
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(str(p.relative_to(base)).replace("\\", "/"))
    return sorted(files) if files else ["none"]


class JS3D_Load3DController:
    """Load and interactively preview 3D models (.ply, .glb, .obj, .fbx, .stl)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_file": (_list_3d_files(), {
                    "tooltip": "Select a 3D file from input/3d/ or upload one",
                }),
                "width": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
            },
            "optional": {
                "snapshot_data": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Auto-filled by the 3D viewer (JSON with base64 image/mask/normal + camera)",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "IMAGE", "STRING", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "mesh_path", "normal_map", "camera_info", "width", "height")
    FUNCTION = "execute"
    CATEGORY = "3d"
    DESCRIPTION = "Load a 3D model file and display an interactive viewer with gizmo controls."

    @classmethod
    def IS_CHANGED(cls, model_file, width, height, snapshot_data=""):
        path = _resolve_path(model_file)
        if os.path.exists(path):
            m = hashlib.md5()
            m.update(str(os.path.getmtime(path)).encode())
            m.update(snapshot_data.encode())
            return m.hexdigest()
        return ""

    def execute(self, model_file, width, height, snapshot_data=""):
        mesh_path = _resolve_path(model_file)

        if snapshot_data and snapshot_data.strip():
            try:
                data = json.loads(snapshot_data)
                image = _decode_base64_image(data.get("image", ""), width, height)
                mask = _decode_base64_mask(data.get("mask", ""), width, height)
                normal = _decode_base64_image(data.get("normal", ""), width, height)
                cam = json.dumps(data.get("camera", {}))
                return (image, mask, mesh_path, normal, cam, width, height)
            except Exception:
                pass

        blank_img = torch.zeros(1, height, width, 3, dtype=torch.float32)
        blank_mask = torch.zeros(1, height, width, dtype=torch.float32)
        return (blank_img, blank_mask, mesh_path, blank_img.clone(), "{}", width, height)


def _resolve_path(model_file):
    if os.path.isabs(model_file) and os.path.exists(model_file):
        return model_file
    return os.path.join(folder_paths.get_input_directory(), model_file)


def _decode_base64_image(b64_str, w, h):
    if not b64_str:
        return torch.zeros(1, h, w, 3, dtype=torch.float32)
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        raw = base64.b64decode(b64_str)
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = np.array(img).astype(np.float32) / 255.0
        return torch.from_numpy(arr).unsqueeze(0)
    except Exception:
        return torch.zeros(1, h, w, 3, dtype=torch.float32)


def _decode_base64_mask(b64_str, w, h):
    if not b64_str:
        return torch.zeros(1, h, w, dtype=torch.float32)
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        raw = base64.b64decode(b64_str)
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raw)).convert("L")
        arr = np.array(img).astype(np.float32) / 255.0
        return torch.from_numpy(arr).unsqueeze(0)
    except Exception:
        return torch.zeros(1, h, w, dtype=torch.float32)


NODE_CLASS_MAPPINGS = {
    "JS3D_Load3DController": JS3D_Load3DController,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JS3D_Load3DController": "Load 3D Controller",
}
