"""媒体工具：图片元数据"""
from __future__ import annotations

import struct

from .base import safe_path



def image_info(path: str) -> dict:
    p = safe_path(path)
    data =p.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        fmt = "PNG"
        w, h = struct.unpack(">II", data[16:24])
    elif data[:2] == b"\xff\xd8":
        fmt, w, h = "JPEG", 0, 0
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xc0, 0xc1, 0xc2, 0xc3):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                break
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
        if not w:
            raise ValueError(f"JPEG 里没找到尺寸信息")
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        fmt = "GIF"
        w, h = struct.unpack("<HH",data[6 : 10])
    else:
        raise ValueError(f"只支持 PNG / JPEG / GIF")
    return {"path": str(p), "format": fmt, "width": w, "height": h, "bytes": len(data)}



SPECS = [
    {
        "type": "function",
        "function": {
            "name": "image_info",
            "descrption": (
                "读取图片文件的格式、宽度、高度、字节数。只能拿到元数据; "
                "要识别图片内容，需要用户吧图片通过 --image 传入。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "图片路径 (PNG/JPEG/GIF) "},
                },
                "required": ["path"],
            },
        },
    },
]

IMPL = {"image_info": image_info}
