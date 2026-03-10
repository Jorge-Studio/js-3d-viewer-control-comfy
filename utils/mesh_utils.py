"""Mesh loading and format conversion via trimesh."""

import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".ply", ".glb", ".gltf", ".obj", ".fbx", ".stl", ".splat"}

EXPORT_FORMATS = {
    "glb": ".glb",
    "obj": ".obj",
    "stl": ".stl",
    "ply": ".ply",
}


def convert_mesh(source_path: str, target_format: str, output_dir: str,
                 filename_prefix: str = "exported_3d") -> str:
    """Convert a mesh file to a different format using trimesh.

    Returns the path to the exported file.
    """
    import trimesh

    ext = EXPORT_FORMATS.get(target_format)
    if ext is None:
        raise ValueError(f"Unsupported target format: {target_format}")

    scene_or_mesh = trimesh.load(source_path)

    if isinstance(scene_or_mesh, trimesh.Scene):
        if target_format == "glb":
            out_path = os.path.join(output_dir, f"{filename_prefix}{ext}")
            scene_or_mesh.export(out_path, file_type="glb")
            return out_path
        meshes = list(scene_or_mesh.geometry.values())
        if meshes:
            mesh = trimesh.util.concatenate(meshes)
        else:
            raise ValueError("Scene contains no geometry")
    else:
        mesh = scene_or_mesh

    out_path = os.path.join(output_dir, f"{filename_prefix}{ext}")
    mesh.export(out_path, file_type=target_format)
    return out_path
