"""JS3D_CompositeOnImage — overlay a rendered 3D model onto a background."""

import torch

from ..utils.render_utils import composite_images


class JS3D_CompositeOnImage:
    """Composite a rendered 3D foreground onto a background image using a mask."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "foreground": ("IMAGE",),
                "mask": ("MASK",),
                "background": ("IMAGE",),
                "x_offset": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 1}),
                "y_offset": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 1}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 10.0, "step": 0.01}),
                "blend_mode": (["normal", "multiply", "screen", "overlay"],),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "3d"
    DESCRIPTION = "Composite a rendered 3D model onto a background image."

    def execute(self, foreground, mask, background, x_offset, y_offset,
                scale, blend_mode, opacity):
        result = composite_images(
            foreground, mask, background,
            x_offset=x_offset, y_offset=y_offset,
            scale=scale, opacity=opacity, blend_mode=blend_mode,
        )
        return (result,)


NODE_CLASS_MAPPINGS = {
    "JS3D_CompositeOnImage": JS3D_CompositeOnImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JS3D_CompositeOnImage": "Composite 3D on Image",
}
