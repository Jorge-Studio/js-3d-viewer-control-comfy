"""Server-side rendering helpers for compositing."""

import numpy as np
import torch


def _resize_tensor(img, new_w, new_h):
    from PIL import Image
    arr = img[0].numpy()
    if arr.ndim == 3 and arr.shape[2] == 3:
        pil = Image.fromarray((arr * 255).astype(np.uint8))
    else:
        pil = Image.fromarray((arr * 255).astype(np.uint8))
    pil = pil.resize((new_w, new_h), Image.LANCZOS)
    return torch.from_numpy(np.array(pil).astype(np.float32) / 255.0).unsqueeze(0)


def _resize_mask(m, new_w, new_h):
    from PIL import Image
    arr = m[0].numpy()
    pil = Image.fromarray((arr * 255).astype(np.uint8))
    pil = pil.resize((new_w, new_h), Image.LANCZOS)
    return torch.from_numpy(np.array(pil).astype(np.float32) / 255.0).unsqueeze(0)


def composite_images(foreground: torch.Tensor, mask: torch.Tensor,
                     background: torch.Tensor, x_offset: int = 0,
                     y_offset: int = 0, scale: float = 1.0,
                     opacity: float = 1.0, blend_mode: str = "normal",
                     fit_mode: str = "fit") -> torch.Tensor:
    """Alpha-composite foreground onto background using mask.

    All tensors are in ComfyUI format: (B, H, W, C) float32 [0,1].
    Mask is (B, H, W) float32 [0,1].

    fit_mode controls how the foreground is placed:
      - "fit": scale fg to fit inside bg, then center + offset
      - "fill": scale fg to cover bg entirely, then center + offset
      - "stretch": stretch fg to exactly match bg dimensions
      - "none": use fg at original size, placed at top-left + offset
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

    if fit_mode == "stretch":
        fg = _resize_tensor(fg, bg_w, bg_h)
        m = _resize_mask(m, bg_w, bg_h)
        fg_h, fg_w = bg_h, bg_w
    elif fit_mode in ("fit", "fill"):
        ratio_w = bg_w / fg_w
        ratio_h = bg_h / fg_h
        r = min(ratio_w, ratio_h) if fit_mode == "fit" else max(ratio_w, ratio_h)
        new_w = max(1, int(fg_w * r))
        new_h = max(1, int(fg_h * r))
        fg = _resize_tensor(fg, new_w, new_h)
        m = _resize_mask(m, new_w, new_h)
        fg_h, fg_w = new_h, new_w

    if scale != 1.0:
        new_h = max(1, int(fg_h * scale))
        new_w = max(1, int(fg_w * scale))
        fg = _resize_tensor(fg, new_w, new_h)
        m = _resize_mask(m, new_w, new_h)
        fg_h, fg_w = new_h, new_w

    if fit_mode != "none":
        cx = (bg_w - fg_w) // 2 + x_offset
        cy = (bg_h - fg_h) // 2 + y_offset
    else:
        cx = x_offset
        cy = y_offset

    x1 = max(0, cx)
    y1 = max(0, cy)
    x2 = min(bg_w, cx + fg_w)
    y2 = min(bg_h, cy + fg_h)

    if x2 <= x1 or y2 <= y1:
        return bg

    src_x1 = x1 - cx
    src_y1 = y1 - cy
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
