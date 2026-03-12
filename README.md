# JS 3D Viewer Control for ComfyUI

A ComfyUI custom node suite for loading, viewing, compositing, and converting 3D models — with a focus on **Gaussian Splatting PLY** files. Position your 3D model interactively, composite it onto any background image, and convert Gaussian Splat point clouds into textured 3D meshes.

## Nodes

| Node | Purpose |
|------|---------|
| **Load 3D Controller** | Interactive 3D viewer with orbit, gizmo, and snapshot capture. Outputs a clean transparent render + mask at your specified resolution. |
| **Composite 3D on Image** | Alpha-composites the 3D render onto a background image. Auto-fits/centers by default. |
| **Gaussian Splat to Mesh** | Converts Gaussian Splatting PLY point clouds into textured 3D meshes via Poisson Surface Reconstruction. |
| **Preview 3D** | Output-only viewer for inspecting meshes from upstream nodes. |
| **Export 3D Format** | Convert between GLB, OBJ, STL, PLY with a download button. |
| **Camera Rig 3D** | Define camera parameters (position, target, FOV) to control the viewer. |

## Supported Formats

`.ply` (Gaussian Splatting + standard), `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl`, `.splat`

## Quick Start

1. **Install**: Clone into `ComfyUI/custom_nodes/` and install requirements.
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/Jorge-Studio/js-3d-viewer-control-comfy.git
   cd js-3d-viewer-control-comfy
   pip install -r requirements.txt
   ```

2. **Add a 3D file**: Place your `.ply` / `.glb` / etc. in `ComfyUI/input/3d/`.

3. **Load a workflow**: Drag any workflow from `workflows/` onto the ComfyUI canvas.

4. **Position your model**: Use the interactive 3D viewer — orbit (LMB), pan (RMB), zoom (scroll). Use T/R/S/Q keys for translate, rotate, scale, or orbit gizmo modes.

5. **Queue**: Hit Queue. The viewer automatically captures a transparent snapshot at your specified output resolution before execution.

## Gaussian Splat to Mesh Conversion

The `Gaussian Splat to Mesh` node converts point cloud data into a proper 3D mesh you can interact with, texture, and export. The pipeline:

```
Gaussian PLY → Extract Points + Colours → Filter by Opacity
  → Simplify Point Cloud → Estimate Normals
  → Screened Poisson Surface Reconstruction
  → Clean Mesh → Transfer Vertex Colours to Texture
  → Export as OBJ/GLB with texture
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| simplify_ratio | 0.1 | Fraction of points to keep (0.1 = 10%). Lower = faster but coarser. |
| simplify_method | voxel | `voxel` for uniform grid, `random` for random subsample. |
| poisson_depth | 8 | Octree depth for Poisson reconstruction. Higher = more detail, slower. |
| density_quantile | 0.1 | Remove vertices below this density percentile (removes artefacts). |
| normal_neighbours | 30 | KNN for normal estimation. |
| clean_mesh | true | Remove degenerate triangles, isolated components, non-manifold edges. |
| texture | true | Generate UV-mapped texture atlas from vertex colours (requires pymeshlab). |
| texture_size | 4096 | Texture atlas resolution. |
| target_format | obj | Output format: OBJ (with texture), GLB (self-contained), or PLY (vertex colours only). |

## Viewer Features

### Controls
| Input | Action |
|-------|--------|
| Left Mouse | Orbit camera |
| Right Mouse | Pan camera |
| Scroll | Zoom |
| T | Translate gizmo |
| R | Rotate gizmo |
| S | Scale gizmo |
| Q | Orbit mode (no gizmo) |

### Panels
- **Scene**: Grid, background colour, axes, image ratio (1:1, 16:9, 4:3, etc.)
- **Model**: Material mode, up axis (all 6 directions: +/-X, +/-Y, +/-Z), opacity, point size
- **Camera**: Perspective/orthographic, FOV, focal length (mm), position, target
- **Light**: Ambient/directional intensity, colour, position

### View Presets
Front (F), Top, and Side view buttons for quick camera positioning.

### Output Resolution
The `width` and `height` inputs on the Load 3D Controller node control the actual output image resolution. The snapshot is rendered at the specified dimensions regardless of the viewer widget size on the canvas.

## Composite Fit Modes

The `Composite 3D on Image` node has a `fit_mode` dropdown:
- **fit** (default): Scale the 3D render to fit inside the background, centered
- **fill**: Scale to cover the entire background
- **stretch**: Stretch to exactly match background dimensions
- **none**: Use original render size, placed at top-left corner

## Workflows

All workflows are in the `workflows/` folder. Drag any onto the ComfyUI canvas.

| # | Workflow | What it tests |
|---|----------|---------------|
| 01 | `01_view_and_render.json` | Load any 3D file, position it interactively, render a clean transparent PNG. Tests viewer controls, gizmo, axis options, focal length, image ratio, view presets. |
| 02 | `02_composite_on_background.json` | Load a background image + 3D model, composite the model onto the background with fit/scale/offset controls. Tests live background preview in viewer. |
| 03 | `03_gaussian_to_mesh.json` | Convert a Gaussian Splatting PLY to a textured mesh via Poisson reconstruction, preview the result, and export/download it. Tests the full conversion pipeline. |
| 04 | `04_export_and_convert.json` | Load any 3D file, convert it to another format (GLB, OBJ, STL, PLY), preview the result, and download it. |
| 05 | `05_camera_rig.json` | Define exact camera position/FOV/target via Camera Rig node and apply to a Preview 3D viewer. Save the rendered output from a controlled angle. |
| 06 | `06_full_scene_composition.json` | Full pipeline: 3D model composited on background, then framed and positioned with Pan & Scan Layers for final output. |

## Requirements

- ComfyUI
- Python packages: `trimesh`, `numpy`, `Pillow`, `pygltflib`, `open3d`, `pymeshlab`

## License

MIT
