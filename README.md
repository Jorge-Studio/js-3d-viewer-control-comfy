# JS 3D Viewer Control for ComfyUI

Interactive 3D model viewer and controller nodes for ComfyUI. Load, preview, manipulate, export, and composite 3D models — with full support for **Gaussian Splatting PLY** files, standard meshes (GLB, OBJ, FBX, STL), and point clouds.

## Nodes

### Load 3D Controller (`JS3D_Load3DController`)
The primary node. Load any supported 3D file and interact with it in a built-in Three.js viewer.

**Features:**
- Interactive 3D viewport with orbit, pan, and zoom
- **Gizmo controls** — translate (T), rotate (R), scale (S) with keyboard shortcuts
- **Scene panel** — grid, background color, axes toggle
- **Model panel** — material modes (original, wireframe, normal map, point cloud, flat), up-axis, opacity, scale
- **Camera panel** — perspective/orthographic, FOV control
- **Light panel** — ambient and directional intensity, light color
- **Snapshot capture** — renders image, mask, and normal map for downstream use

**Supported formats:** `.ply`, `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl`, `.splat`

**Outputs:** `image`, `mask`, `mesh_path`, `normal_map`, `camera_info`

### Preview 3D (`JS3D_Preview3D`)
Output-only preview node. Connect `mesh_path` from any upstream node to visualize the model.

### Export 3D Format (`JS3D_ExportFormat`)
Convert 3D files between formats using trimesh.

**Supported conversions:** GLB, OBJ, STL, PLY

*Note: Gaussian Splatting PLY files (point clouds with spherical harmonics) cannot be converted to mesh formats and will pass through unchanged.*

### Composite 3D on Image (`JS3D_CompositeOnImage`)
Alpha-composite a rendered 3D model onto a background image.

**Features:** offset, scale, blend modes (normal, multiply, screen, overlay), opacity control.

### Camera Rig 3D (`JS3D_CameraRig`)
Define camera parameters (type, FOV, position, target, zoom) and pass them to other 3D nodes.

## Installation

### From GitHub
```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/Jorge-Studio/js-3d-viewer-control-comfy.git
cd js-3d-viewer-control-comfy
pip install -r requirements.txt
```

### Manual
1. Download or unzip into `ComfyUI/custom_nodes/js-3d-viewer-control-comfy/`
2. Install dependencies: `pip install -r requirements.txt`
3. Restart ComfyUI

## Usage

1. Place 3D files in `ComfyUI/input/3d/` or drag-and-drop onto the node
2. Add a **Load 3D Controller** node
3. Select your file from the dropdown
4. Use the interactive viewport:
   - **Left-click drag** — orbit
   - **Right-click drag** — pan
   - **Scroll** — zoom
   - **T/R/S/Q** — switch gizmo mode (translate/rotate/scale/orbit-only)
5. Click the camera icon to capture a snapshot for downstream nodes
6. Connect outputs to **Preview 3D**, **Export 3D Format**, or **Composite 3D on Image**

## Gaussian Splatting

PLY files with Gaussian Splatting data (containing `f_dc_0`, `rot_0`, `scale_0` properties) are automatically detected and rendered as point clouds with vertex colors. The splat viewer uses additive blending for a volumetric appearance.

For best results, export your Gaussian Splatting scenes from tools like:
- 3D Gaussian Splatting (INRIA)
- Nerfstudio
- COLMAP + 3DGS training pipelines

## Dependencies

- **Python:** `trimesh`, `numpy`, `Pillow`, `pygltflib`
- **JavaScript (CDN, no install):** Three.js 0.170, OrbitControls, TransformControls, GLTFLoader, OBJLoader, FBXLoader, STLLoader, PLYLoader

## Example Workflows

- `workflows/test_load_preview.json` — Load + Preview + Camera Rig + Export
- `workflows/test_composite.json` — Load + Composite on background image

## License

MIT
