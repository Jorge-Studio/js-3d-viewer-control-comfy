"""Server-side rendering helpers for compositing."""

import numpy as np
import torch


def composite_images(foreground: torch.Tensor, mask: torch.Tensor,
                     background: torch.Tensor, x_offset: int = 0,
                     y_offset: int = 0, scale: float = 1.0,
                     opacity: float = 1.0,
                     blend_mode: str = "normal") -> torch.Tensor:
    """Alpha-composite foreground onto background using mask.

    All tensors are in ComfyUI format: (B, H, W, C) float32 [0,1].
    Mask is (B, H, W) float32 [0,1].
    """
    bg = background.clone()
    fg = foreground.clone()
    m = mask.clone()

    if fg.dim() == 3:
        fg = fg.unsqueeze(0)
    if bg.dim() == 3:
        bg = bg.unsqueeze(0)
    if m.dim() == 2:
        m = m.unsqueeze(0)

    _, fg_h, fg_w, _ = fg.shape
    _, bg_h, bg_w, _ = bg.shape

    if scale != 1.0:
        new_h = max(1, int(fg_h * scale))
        new_w = max(1, int(fg_w * scale))
        fg_np = fg[0].numpy()
        from PIL import Image
        fg_pil = Image.fromarray((fg_np * 255).astype(np.uint8))
        fg_pil = fg_pil.resize((new_w, new_h), Image.LANCZOS)
        fg = torch.from_numpy(np.array(fg_pil).astype(np.float32) / 255.0).unsqueeze(0)

        m_np = m[0].numpy()
        m_pil = Image.fromarray((m_np * 255).astype(np.uint8))
        m_pil = m_pil.resize((new_w, new_h), Image.LANCZOS)
        m = torch.from_numpy(np.array(m_pil).astype(np.float32) / 255.0).unsqueeze(0)

        fg_h, fg_w = new_h, new_w

    x1 = max(0, x_offset)
    y1 = max(0, y_offset)
    x2 = min(bg_w, x_offset + fg_w)
    y2 = min(bg_h, y_offset + fg_h)

    if x2 <= x1 or y2 <= y1:
        return bg

    src_x1 = x1 - x_offset
    src_y1 = y1 - y_offset
    src_x2 = src_x1 + (x2 - x1)
    src_y2 = src_y1 + (y2 - y1)

    fg_region = fg[:, src_y1:src_y2, src_x1:src_x2, :]
    mask_region = m[:, src_y1:src_y2, src_x1:src_x2].unsqueeze(-1) * opacity
    bg_region = bg[:, y1:y2, x1:x2, :]

    if blend_mode == "multiply":
        blended = fg_region * bg_region
    elif blend_mode == "screen":
        blended = 1.0 - (1.0 - fg_region) * (1.0 - bg_region)
    elif blend_mode == "overlay":
        low = 2.0 * fg_region * bg_region
        high = 1.0 - 2.0 * (1.0 - fg_region) * (1.0 - bg_region)
        blended = torch.where(bg_region < 0.5, low, high)
    else:
        blended = fg_region

    bg[:, y1:y2, x1:x2, :] = bg_region * (1.0 - mask_region) + blended * mask_region
    return bg.clamp(0, 1)
