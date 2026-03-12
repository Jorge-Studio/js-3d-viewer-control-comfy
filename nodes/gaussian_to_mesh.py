"""JS3D_GaussianToMesh — convert a Gaussian Splatting PLY to a textured mesh."""

import os
import importlib.util

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_DIR = os.path.dirname(_THIS_DIR)
_UTILS_PATH = os.path.join(_PACKAGE_DIR, "utils", "gaussian_mesh_utils.py")

_gaussian_to_mesh_fn = None


def _get_gaussian_to_mesh():
    """Load gaussian_mesh_utils by file path to avoid relative-import issues
    with ComfyUI's module loader and hyphenated directory names."""
    global _gaussian_to_mesh_fn
    if _gaussian_to_mesh_fn is not None:
        return _gaussian_to_mesh_fn
    spec = importlib.util.spec_from_file_location("gaussian_mesh_utils", _UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _gaussian_to_mesh_fn = mod.gaussian_to_mesh
    return _gaussian_to_mesh_fn


class JS3D_GaussianToMesh:
    """Convert a Gaussian Splatting point cloud (.ply) into a textured 3D mesh."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh_path": ("STRING", {
                    "default": "",
                    "tooltip": "Path to a Gaussian Splatting PLY file",
                }),
                "simplify_ratio": ("FLOAT", {
                    "default": 0.1, "min": 0.01, "max": 1.0, "step": 0.01,
                    "tooltip": "Fraction of points to keep (0.1 = 10 percent). Lower is faster but coarser.",
                }),
                "simplify_method": (["voxel", "random"], {
                    "default": "voxel",
                    "tooltip": "voxel: uniform grid sampling. random: random subsample.",
                }),
                "poisson_depth": ("INT", {
                    "default": 8, "min": 4, "max": 12, "step": 1,
                    "tooltip": "Poisson octree depth. Higher gives more detail but is slower.",
                }),
                "density_quantile": ("FLOAT", {
                    "default": 0.1, "min": 0.0, "max": 0.5, "step": 0.01,
                    "tooltip": "Remove vertices below this density percentile to clean artefacts.",
                }),
                "normal_neighbours": ("INT", {
                    "default": 30, "min": 5, "max": 100, "step": 5,
                    "tooltip": "Number of neighbours for normal estimation.",
                }),
                "clean_mesh": ("BOOLEAN", {"default": True,
                    "tooltip": "Remove degenerate triangles, small components, non-manifold edges.",
                }),
                "texture": ("BOOLEAN", {"default": True,
                    "tooltip": "Generate a UV-mapped texture from vertex colours (requires pymeshlab).",
                }),
                "texture_size": ("INT", {
                    "default": 4096, "min": 512, "max": 8192, "step": 512,
                    "tooltip": "Texture atlas resolution in pixels.",
                }),
                "target_format": (["obj", "glb", "ply"], {
                    "default": "obj",
                    "tooltip": "Output format. OBJ includes texture. GLB is self-contained. PLY has vertex colours only.",
                }),
                "filename_prefix": ("STRING", {
                    "default": "gs_mesh",
                    "tooltip": "Prefix for the output filename.",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("mesh_path",)
    FUNCTION = "execute"
    CATEGORY = "3d"
    OUTPUT_NODE = True
    DESCRIPTION = "Convert a Gaussian Splatting PLY point cloud into a textured 3D mesh using Poisson Surface Reconstruction."

    def execute(self, mesh_path, simplify_ratio, simplify_method, poisson_depth,
                density_quantile, normal_neighbours, clean_mesh, texture,
                texture_size, target_format, filename_prefix):

        import folder_paths

        gaussian_to_mesh = _get_gaussian_to_mesh()

        if not mesh_path or not os.path.isfile(mesh_path):
            resolved = os.path.join(folder_paths.get_input_directory(), mesh_path)
            if os.path.isfile(resolved):
                mesh_path = resolved
            else:
                raise FileNotFoundError(
                    f"Gaussian PLY file not found: {mesh_path}"
                )

        output_dir = os.path.join(folder_paths.get_output_directory(), "3d_meshes")

        result_path = gaussian_to_mesh(
            ply_path=mesh_path,
            output_dir=output_dir,
            filename_prefix=filename_prefix,
            simplify_ratio=simplify_ratio,
            simplify_method=simplify_method,
            poisson_depth=poisson_depth,
            density_quantile=density_quantile,
            normal_neighbours=normal_neighbours,
            do_clean=clean_mesh,
            do_texture=texture,
            texture_size=texture_size,
            target_format=target_format,
        )

        basename = os.path.basename(result_path)

        # Auto-copy to input/3d/ so Load 3D Controller can find it
        input_3d_dir = os.path.join(folder_paths.get_input_directory(), "3d")
        os.makedirs(input_3d_dir, exist_ok=True)
        input_copy = os.path.join(input_3d_dir, basename)
        try:
            import shutil
            shutil.copy2(result_path, input_copy)
            # Also copy texture files if they exist (OBJ + MTL + PNG)
            result_dir = os.path.dirname(result_path)
            name_no_ext = os.path.splitext(basename)[0]
            for ext in ['.mtl', '.png', '.jpg']:
                companion = os.path.join(result_dir, name_no_ext + ext)
                if os.path.isfile(companion):
                    shutil.copy2(companion, os.path.join(input_3d_dir, name_no_ext + ext))
            print(f"[JS3D GS→Mesh] Copied to input/3d/{basename} for Load 3D Controller")
        except Exception as e:
            print(f"[JS3D GS→Mesh] Could not copy to input/3d/: {e}")

        return {
            "ui": {
                "js3d_export": [{
                    "filename": basename,
                    "subfolder": "3d_meshes",
                    "type": "output",
                    "format": target_format,
                    "size": os.path.getsize(result_path) if os.path.isfile(result_path) else 0,
                }]
            },
            "result": (result_path,),
        }


NODE_CLASS_MAPPINGS = {
    "JS3D_GaussianToMesh": JS3D_GaussianToMesh,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JS3D_GaussianToMesh": "Gaussian Splat to Mesh",
}
