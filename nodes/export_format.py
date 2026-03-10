"""JS3D_ExportFormat — convert 3D files between formats."""

import os
import folder_paths

from ..utils.ply_utils import is_gaussian_splatting_ply
from ..utils.mesh_utils import convert_mesh, EXPORT_FORMATS


class JS3D_ExportFormat:
    """Convert a 3D model between formats (GLB, OBJ, STL, PLY)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh_path": ("STRING", {"default": ""}),
                "target_format": (list(EXPORT_FORMATS.keys()),),
                "filename_prefix": ("STRING", {"default": "exported_3d"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("exported_path",)
    FUNCTION = "execute"
    CATEGORY = "3d"
    OUTPUT_NODE = True
    DESCRIPTION = "Convert a 3D model file to a different format and provide a download link."

    def execute(self, mesh_path, target_format, filename_prefix):
        if not os.path.exists(mesh_path):
            raise FileNotFoundError(f"Source file not found: {mesh_path}")

        if mesh_path.lower().endswith(".ply") and is_gaussian_splatting_ply(mesh_path):
            print("[JS3D Export] WARNING: Gaussian Splatting PLY cannot be converted "
                  "to mesh formats. Passing through original file.")
            basename = os.path.basename(mesh_path)
            return {
                "ui": {"js3d_export": [{"filename": basename, "subfolder": "",
                                        "type": "input", "format": "ply",
                                        "note": "GS PLY passthrough"}]},
                "result": (mesh_path,),
            }

        output_dir = folder_paths.get_output_directory()
        out_path = convert_mesh(mesh_path, target_format, output_dir, filename_prefix)
        basename = os.path.basename(out_path)
        file_size = os.path.getsize(out_path)
        print(f"[JS3D Export] Converted to {target_format}: {out_path} ({file_size} bytes)")
        return {
            "ui": {"js3d_export": [{"filename": basename, "subfolder": "",
                                    "type": "output", "format": target_format,
                                    "size": file_size}]},
            "result": (out_path,),
        }


NODE_CLASS_MAPPINGS = {
    "JS3D_ExportFormat": JS3D_ExportFormat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JS3D_ExportFormat": "Export 3D Format",
}
