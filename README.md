# JS 3D Viewer Control for ComfyUI

A ComfyUI custom node suite for loading, viewing, and compositing 3D models — with a focus on **Gaussian Splatting PLY** files. Position your 3D model interactively, then composite it onto any background image with full alpha masking.

## Nodes

| Node | Purpose |
|------|---------|
| **Load 3D Controller** | Interactive 3D viewer with orbit, gizmo, and snapshot capture. Outputs a clean transparent render + mask. |
| **Composite 3D on Image** | Alpha-composites the 3D render onto a background image. Auto-fits/centers by default. |
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

5. **Queue**: Hit Queue. The viewer automatically captures a transparent snapshot before execution.

## Workflow: 3D on Background Image

The recommended workflow (`test_3d_layers_scene.json`):

```
LoadImage (background) ──┐
                         ├── Composite 3D on Image ── Pan & Scan Layers ── Preview / Save
Load 3D Controller ──────┘
  (image + mask)
```

- **Load 3D Controller**: Load your 3D model, position it in the viewer
- **Composite 3D on Image**: Automatically fits, centers, and alpha-composites the 3D render onto the background
- **Pan & Scan Layers** (optional): Frame the result at your desired output size and aspect ratio

### Fit Modes

The Composite node has a `fit_mode` dropdown:
- **fit** (default): Scale the 3D render to fit inside the background, centered
- **fill**: Scale to cover the entire background
- **stretch**: Stretch to exactly match background dimensions
- **none**: Use original render size, placed at top-left corner

Use `x_offset` / `y_offset` to nudge the position from center (or from top-left in "none" mode).

## All Workflows

| Workflow | Description |
|----------|-------------|
| `test_3d_layers_scene.json` | Full scene: 3D model composited on background, framed with Pan & Scan Layers |
| `test_3d_on_image.json` | Simple: 3D model composited directly onto a background image |
| `test_load_preview.json` | Basic: Load and preview a 3D model |
| `test_export_and_preview.json` | Export a 3D model to another format with download |
| `test_camera_rig_render.json` | Control the viewer camera via Camera Rig node |
| `test_snapshot_outputs.json` | Inspect all outputs: image, mask, normal map |
| `test_multi_model_composite.json` | Multiple 3D models composited together |

## Viewer Controls

| Input | Action |
|-------|--------|
| Left Mouse | Orbit camera |
| Right Mouse | Pan camera |
| Scroll | Zoom |
| T | Translate gizmo |
| R | Rotate gizmo |
| S | Scale gizmo |
| Q | Orbit mode (no gizmo) |

## Requirements

- ComfyUI
- Python packages: `trimesh`, `numpy`, `Pillow`, `pygltflib`

## License

MIT
