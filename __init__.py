"""JS 3D Viewer Control — ComfyUI custom node suite for 3D model viewing,
control, export, and compositing."""

import os

from .nodes.load_3d_controller import NODE_CLASS_MAPPINGS as load_nodes
from .nodes.load_3d_controller import NODE_DISPLAY_NAME_MAPPINGS as load_names
from .nodes.preview_3d import NODE_CLASS_MAPPINGS as preview_nodes
from .nodes.preview_3d import NODE_DISPLAY_NAME_MAPPINGS as preview_names
from .nodes.export_format import NODE_CLASS_MAPPINGS as export_nodes
from .nodes.export_format import NODE_DISPLAY_NAME_MAPPINGS as export_names
from .nodes.composite_on_image import NODE_CLASS_MAPPINGS as composite_nodes
from .nodes.composite_on_image import NODE_DISPLAY_NAME_MAPPINGS as composite_names
from .nodes.camera_rig import NODE_CLASS_MAPPINGS as camera_nodes
from .nodes.camera_rig import NODE_DISPLAY_NAME_MAPPINGS as camera_names

NODE_CLASS_MAPPINGS = {
    **load_nodes,
    **preview_nodes,
    **export_nodes,
    **composite_nodes,
    **camera_nodes,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **load_names,
    **preview_names,
    **export_names,
    **composite_names,
    **camera_names,
}

WEB_DIRECTORY = "./web"

# --- Register API routes to serve viewer HTML reliably --------------------
# Some ComfyUI installations don't serve HTML from the extensions static
# directory, so we register explicit routes as a guaranteed fallback.
_HTML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "html")

try:
    from server import PromptServer
    from aiohttp import web

    @PromptServer.instance.routes.get("/js3d/viewer/{filename}")
    async def _serve_viewer_html(request):
        name = request.match_info["filename"]
        if not name.endswith(".html"):
            name += ".html"
        safe = os.path.basename(name)
        fpath = os.path.join(_HTML_DIR, safe)
        if os.path.isfile(fpath):
            return web.FileResponse(fpath, headers={"Content-Type": "text/html"})
        return web.Response(status=404, text="Viewer not found")

except Exception:
    pass  # PromptServer may not be available during offline tests

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
