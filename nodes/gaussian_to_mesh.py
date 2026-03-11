"""JS3D_GaussianToMesh — convert a Gaussian Splatting PLY to a textured mesh."""

import os
import folder_paths


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
                    "tooltip": "Fraction of points to keep (0.1 = 10%). Lower = faster, coarser mesh.",
                }),
                "simplify_method": (["voxel", "random"], {
                    "default": "voxel",
                    "tooltip": "voxel: uniform grid sampling. random: random subsample.",
                }),
                "poisson_depth": ("INT", {
                    "default": 8, "min": 4, "max": 12, "step": 1,
                    "tooltip": "Poisson octree depth. Higher = more detail, slower. 8 is a good default.",
                }),
                "density_quantile": ("FLOAT", {
                    "default": 0.1, "min": 0.0, "max": 0.5, "step": 0.01,
                    "tooltip": "Remove vertices below this density percentile (removes artefacts).",
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
                    "tooltip": "Output format. OBJ includes texture; GLB is self-contained; PLY is vertex-colour only.",
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
    DESCRIPTION = (
        "Convert a Gaussian Splatting PLY point cloud into a textured 3D mesh "
        "using Poisson Surface Reconstruction. Pipeline: extract points → "
        "simplify → estimate normals → Poisson meshing → clean → texture → export."
    )

    def execute(self, mesh_path, simplify_ratio, simplify_method, poisson_depth,
                density_quantile, normal_neighbours, clean_mesh, texture,
                texture_size, target_format, filename_prefix):

        if not mesh_path or not os.path.isfile(mesh_path):
            resolved = os.path.join(folder_paths.get_input_directory(), mesh_path)
            if os.path.isfile(resolved):
                mesh_path = resolved
            else:
                raise FileNotFoundError(
                    f"Gaussian PLY file not found: {mesh_path}"
                )

        from ..utils.gaussian_mesh_utils import gaussian_to_mesh

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
