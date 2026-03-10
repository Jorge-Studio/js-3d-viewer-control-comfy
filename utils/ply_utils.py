"""PLY file utilities — detect Gaussian Splatting vs standard mesh."""

import struct
from pathlib import Path

GAUSSIAN_SPLAT_PROPERTIES = {"f_dc_0", "rot_0", "scale_0", "opacity"}


def is_gaussian_splatting_ply(filepath: str) -> bool:
    """Read the PLY header and check for 3DGS-specific properties."""
    try:
        with open(filepath, "rb") as f:
            header_bytes = b""
            while True:
                line = f.readline()
                if not line:
                    break
                header_bytes += line
                if b"end_header" in line:
                    break

            header = header_bytes.decode("ascii", errors="ignore").lower()
            found = sum(1 for prop in GAUSSIAN_SPLAT_PROPERTIES if prop in header)
            return found >= 3
    except Exception:
        return False


def get_ply_info(filepath: str) -> dict:
    """Extract basic info from a PLY file header."""
    info = {
        "format": "unknown",
        "vertex_count": 0,
        "face_count": 0,
        "is_gaussian_splatting": False,
        "properties": [],
    }
    try:
        with open(filepath, "rb") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                text = line.decode("ascii", errors="ignore").strip()
                if text.startswith("format "):
                    info["format"] = text.split(" ", 1)[1]
                elif text.startswith("element vertex"):
                    info["vertex_count"] = int(text.split()[-1])
                elif text.startswith("element face"):
                    info["face_count"] = int(text.split()[-1])
                elif text.startswith("property "):
                    info["properties"].append(text)
                elif text == "end_header":
                    break
    except Exception:
        pass

    info["is_gaussian_splatting"] = is_gaussian_splatting_ply(filepath)
    return info
