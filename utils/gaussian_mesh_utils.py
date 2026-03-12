"""Gaussian Splatting PLY → Textured Mesh conversion pipeline.

Uses Open3D for point-cloud processing and Poisson surface reconstruction,
and PyMeshLab for UV parametrization and vertex-color-to-texture transfer.
"""

import os
import struct
import tempfile
from pathlib import Path

import numpy as np

SH_C0 = 0.28209479177387814


# ---------------------------------------------------------------------------
# Step 1 — Extract positions + colours from a Gaussian Splatting PLY
# ---------------------------------------------------------------------------

def _parse_ply_header(data: bytes):
    """Parse a binary PLY header, return property map and metadata."""
    marker = b"end_header\n"
    idx = data.find(marker)
    if idx < 0:
        return None
    header_end = idx + len(marker)
    header_text = data[:header_end].decode("ascii", errors="replace")
    lines = header_text.split("\n")

    fmt = ""
    vertex_count = 0
    props = []
    in_vertex = False

    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = parts[1]
        elif parts[0] == "element":
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                vertex_count = int(parts[2])
        elif parts[0] == "property" and in_vertex and parts[1] != "list":
            props.append((parts[1], parts[2]))

    type_sizes = {
        "float": 4, "float32": 4, "double": 8, "float64": 8,
        "uchar": 1, "uint8": 1, "char": 1, "int8": 1,
        "ushort": 2, "uint16": 2, "short": 2, "int16": 2,
        "uint": 4, "uint32": 4, "int": 4, "int32": 4,
    }

    stride = 0
    prop_map = {}
    for ptype, pname in props:
        prop_map[pname] = (stride, ptype)
        stride += type_sizes.get(ptype, 4)

    little_endian = "little" in fmt
    is_gs = all(k in prop_map for k in ("f_dc_0", "f_dc_1", "f_dc_2"))

    return {
        "vertex_count": vertex_count,
        "prop_map": prop_map,
        "stride": stride,
        "data_offset": header_end,
        "is_gs": is_gs,
        "little_endian": little_endian,
        "format": fmt,
    }


def _read_value(buf, offset, ptype, le):
    bo = "<" if le else ">"
    if ptype in ("float", "float32"):
        return struct.unpack_from(f"{bo}f", buf, offset)[0]
    if ptype in ("double", "float64"):
        return struct.unpack_from(f"{bo}d", buf, offset)[0]
    if ptype in ("uchar", "uint8"):
        return struct.unpack_from("B", buf, offset)[0]
    if ptype in ("int", "int32"):
        return struct.unpack_from(f"{bo}i", buf, offset)[0]
    return struct.unpack_from(f"{bo}f", buf, offset)[0]


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def load_gaussian_points(ply_path: str, opacity_threshold: float = 0.05):
    """Load a Gaussian Splatting PLY and return (positions, colours) as numpy arrays.

    Returns (N, 3) positions and (N, 3) RGB colours in [0, 1].
    """
    with open(ply_path, "rb") as f:
        data = f.read()

    header = _parse_ply_header(data)
    if header is None:
        raise ValueError("Cannot parse PLY header")

    pm = header["prop_map"]
    stride = header["stride"]
    offset0 = header["data_offset"]
    le = header["little_endian"]
    n = header["vertex_count"]
    is_gs = header["is_gs"]

    if "x" not in pm or "y" not in pm or "z" not in pm:
        raise ValueError("PLY missing position properties (x, y, z)")

    positions = np.empty((n, 3), dtype=np.float32)
    colours = np.empty((n, 3), dtype=np.float32)
    mask = np.ones(n, dtype=bool)

    buf = memoryview(data)

    for i in range(n):
        base = offset0 + i * stride
        px = _read_value(buf, base + pm["x"][0], pm["x"][1], le)
        py = _read_value(buf, base + pm["y"][0], pm["y"][1], le)
        pz = _read_value(buf, base + pm["z"][0], pm["z"][1], le)

        if not (np.isfinite(px) and np.isfinite(py) and np.isfinite(pz)):
            mask[i] = False
            continue

        positions[i] = [px, py, pz]

        if is_gs:
            r = _read_value(buf, base + pm["f_dc_0"][0], pm["f_dc_0"][1], le)
            g = _read_value(buf, base + pm["f_dc_1"][0], pm["f_dc_1"][1], le)
            b = _read_value(buf, base + pm["f_dc_2"][0], pm["f_dc_2"][1], le)
            colours[i] = [
                np.clip(r * SH_C0 + 0.5, 0, 1),
                np.clip(g * SH_C0 + 0.5, 0, 1),
                np.clip(b * SH_C0 + 0.5, 0, 1),
            ]
            if "opacity" in pm:
                op = _read_value(buf, base + pm["opacity"][0], pm["opacity"][1], le)
                if _sigmoid(op) < opacity_threshold:
                    mask[i] = False
        elif "red" in pm:
            r = _read_value(buf, base + pm["red"][0], pm["red"][1], le)
            g = _read_value(buf, base + pm["green"][0], pm["green"][1], le)
            b = _read_value(buf, base + pm["blue"][0], pm["blue"][1], le)
            scale = 255.0 if r > 1.0 or g > 1.0 or b > 1.0 else 1.0
            colours[i] = [r / scale, g / scale, b / scale]
        else:
            colours[i] = [0.7, 0.7, 0.7]

    positions = positions[mask]
    colours = colours[mask]
    return positions, colours


# ---------------------------------------------------------------------------
# Step 2 — Point cloud simplification
# ---------------------------------------------------------------------------

def simplify_point_cloud(positions, colours, ratio=0.1, method="voxel"):
    """Downsample a point cloud.

    method: "voxel" (voxel grid) or "random" (random subsample).
    ratio: target fraction of points to keep (approximate for voxel).
    """
    import open3d as o3d

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(positions)
    pcd.colors = o3d.utility.Vector3dVector(colours)

    if method == "random":
        n_target = max(1000, int(len(positions) * ratio))
        indices = np.random.choice(len(positions), size=min(n_target, len(positions)), replace=False)
        pcd = pcd.select_by_index(indices)
    else:
        bbox = pcd.get_axis_aligned_bounding_box()
        extent = np.max(bbox.get_extent())
        n_current = len(positions)
        n_target = max(1000, int(n_current * ratio))
        voxel_size = extent / (n_target ** (1.0 / 3.0))
        voxel_size = max(voxel_size, extent * 0.0001)
        pcd = pcd.voxel_down_sample(voxel_size)
        if len(pcd.points) < 1000:
            indices = np.random.choice(len(positions), size=min(n_target, len(positions)), replace=False)
            pcd_fallback = o3d.geometry.PointCloud()
            pcd_fallback.points = o3d.utility.Vector3dVector(positions[indices])
            pcd_fallback.colors = o3d.utility.Vector3dVector(colours[indices])
            pcd = pcd_fallback

    return pcd


# ---------------------------------------------------------------------------
# Step 3 — Normal estimation
# ---------------------------------------------------------------------------

def estimate_normals(pcd, nn=30, radius_factor=0.05):
    """Estimate and orient normals on an Open3D PointCloud."""
    import open3d as o3d

    bbox = pcd.get_axis_aligned_bounding_box()
    radius = np.max(bbox.get_extent()) * radius_factor
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=nn)
    )
    pcd.orient_normals_consistent_tangent_plane(k=min(nn, 15))
    return pcd


# ---------------------------------------------------------------------------
# Step 4 — Poisson Surface Reconstruction
# ---------------------------------------------------------------------------

def poisson_reconstruct(pcd, depth=8, density_quantile=0.1):
    """Run Screened Poisson and remove low-density artefacts."""
    import open3d as o3d

    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth, linear_fit=True
    )
    densities = np.asarray(densities)
    threshold = np.quantile(densities, density_quantile)
    vertices_to_remove = densities < threshold
    mesh.remove_vertices_by_mask(vertices_to_remove)

    return mesh


# ---------------------------------------------------------------------------
# Step 5 — Mesh cleaning
# ---------------------------------------------------------------------------

def clean_mesh(mesh):
    """Remove degenerate triangles, non-manifold edges, and small components."""
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    triangle_clusters, cluster_n_tri, _ = mesh.cluster_connected_triangles()
    triangle_clusters = np.asarray(triangle_clusters)
    cluster_n_tri = np.asarray(cluster_n_tri)
    if len(cluster_n_tri) > 1:
        largest = np.argmax(cluster_n_tri)
        triangles_to_remove = triangle_clusters != largest
        mesh.remove_triangles_by_mask(triangles_to_remove)
        mesh.remove_unreferenced_vertices()

    mesh.compute_vertex_normals()
    return mesh


# ---------------------------------------------------------------------------
# Step 6 — Transfer vertex colours and texture via PyMeshLab
# ---------------------------------------------------------------------------

def texture_mesh(pcd_ply_path: str, mesh_ply_path: str, output_path: str,
                 tex_size: int = 4096):
    """UV-parametrise the mesh and transfer vertex colours to a texture atlas.

    Requires pymeshlab. Outputs an OBJ + MTL + PNG.
    """
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(pcd_ply_path)
    ms.load_new_mesh(mesh_ply_path)
    ms.set_current_mesh(1)

    ms.compute_texcoord_parametrization_triangle_trivial_per_wedge(
        textdim=tex_size, border=2
    )
    ms.transfer_attributes_to_texture_per_vertex(
        sourcemesh=0, targetmesh=1, textw=tex_size, texth=tex_size
    )
    ms.save_current_mesh(output_path)


# ---------------------------------------------------------------------------
# Step 7 — Full pipeline
# ---------------------------------------------------------------------------

def gaussian_to_mesh(
    ply_path: str,
    output_dir: str,
    filename_prefix: str = "converted",
    simplify_ratio: float = 0.1,
    simplify_method: str = "voxel",
    poisson_depth: int = 8,
    density_quantile: float = 0.1,
    normal_neighbours: int = 30,
    do_clean: bool = True,
    do_texture: bool = True,
    texture_size: int = 4096,
    target_format: str = "obj",
) -> str:
    """Full Gaussian Splatting PLY → textured mesh pipeline.

    Returns the path to the output mesh file.
    """
    import open3d as o3d

    print(f"[JS3D GS→Mesh] Loading points from {ply_path}")
    positions, colours = load_gaussian_points(ply_path)
    print(f"[JS3D GS→Mesh] Loaded {len(positions):,} points")

    if simplify_ratio < 1.0:
        pcd = simplify_point_cloud(positions, colours, ratio=simplify_ratio,
                                    method=simplify_method)
        print(f"[JS3D GS→Mesh] Simplified to {len(pcd.points):,} points")
    else:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(positions)
        pcd.colors = o3d.utility.Vector3dVector(colours)

    print(f"[JS3D GS→Mesh] Estimating normals (nn={normal_neighbours})")
    pcd = estimate_normals(pcd, nn=normal_neighbours)

    print(f"[JS3D GS→Mesh] Poisson reconstruction (depth={poisson_depth})")
    mesh = poisson_reconstruct(pcd, depth=poisson_depth,
                                density_quantile=density_quantile)
    print(f"[JS3D GS→Mesh] Mesh: {len(mesh.vertices):,} vertices, "
          f"{len(mesh.triangles):,} triangles")

    if do_clean:
        print("[JS3D GS→Mesh] Cleaning mesh")
        mesh = clean_mesh(mesh)
        print(f"[JS3D GS→Mesh] After clean: {len(mesh.vertices):,} vertices, "
              f"{len(mesh.triangles):,} triangles")

    os.makedirs(output_dir, exist_ok=True)

    if do_texture:
        pcd_tmp = os.path.join(output_dir, f"{filename_prefix}_pcd.ply")
        mesh_tmp = os.path.join(output_dir, f"{filename_prefix}_mesh_raw.ply")

        o3d.io.write_point_cloud(pcd_tmp, pcd)

        mesh.paint_uniform_color([0.7, 0.7, 0.7])
        mesh.vertex_colors = o3d.utility.Vector3dVector(
            _transfer_colors_nearest(pcd, mesh)
        )
        o3d.io.write_triangle_mesh(mesh_tmp, mesh)

        obj_path = os.path.join(output_dir, f"{filename_prefix}.obj")
        print(f"[JS3D GS→Mesh] Texturing (size={texture_size})")
        try:
            texture_mesh(pcd_tmp, mesh_tmp, obj_path, tex_size=texture_size)
            print(f"[JS3D GS→Mesh] Textured mesh saved to {obj_path}")
        except Exception as e:
            print(f"[JS3D GS→Mesh] PyMeshLab texturing failed ({e}), "
                  "falling back to vertex colours")
            o3d.io.write_triangle_mesh(obj_path, mesh)

        for tmp in (pcd_tmp, mesh_tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass

        final_path = obj_path
    else:
        out_ext = "glb" if target_format == "glb" else "ply"
        final_path = os.path.join(output_dir, f"{filename_prefix}.{out_ext}")
        o3d.io.write_triangle_mesh(final_path, mesh)

    if target_format == "glb" and final_path.endswith(".obj"):
        glb_path = os.path.join(output_dir, f"{filename_prefix}.glb")
        try:
            import trimesh
            scene = trimesh.load(final_path)
            scene.export(glb_path, file_type="glb")
            final_path = glb_path
            print(f"[JS3D GS→Mesh] Converted to GLB: {glb_path}")
        except Exception as e:
            print(f"[JS3D GS→Mesh] GLB conversion failed ({e}), keeping OBJ")

    print(f"[JS3D GS→Mesh] Done → {final_path}")
    return final_path


def _transfer_colors_nearest(pcd, mesh):
    """Transfer colours from point cloud to mesh vertices via nearest-neighbour."""
    import open3d as o3d

    pcd_tree = o3d.geometry.KDTreeFlann(pcd)
    pcd_colors = np.asarray(pcd.colors)
    mesh_verts = np.asarray(mesh.vertices)
    vert_colors = np.zeros((len(mesh_verts), 3), dtype=np.float64)

    for i, v in enumerate(mesh_verts):
        _, idx, _ = pcd_tree.search_knn_vector_3d(v, 1)
        vert_colors[i] = pcd_colors[idx[0]]

    return vert_colors
