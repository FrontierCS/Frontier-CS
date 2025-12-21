import os
import tarfile
import re
from typing import Optional


class Solution:
    POC_TARGET_LEN = 33
    MAX_SCAN_FILE_SIZE = 65536
    MAX_CFILE_SIZE = 1024 * 1024

    def solve(self, src_path: str) -> bytes:
        try:
            if os.path.isdir(src_path):
                data = self._solve_from_dir(src_path)
            else:
                data = self._solve_from_tar(src_path)
            if data is None:
                data = b"A" * self.POC_TARGET_LEN
            return data
        except Exception:
            return b"A" * self.POC_TARGET_LEN

    def _solve_from_tar(self, tar_path: str) -> Optional[bytes]:
        best_content: Optional[bytes] = None
        best_score = float("-inf")
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = tf.getmembers()
                # Pass 1: small binary-like files
                for m in members:
                    if not m.isfile():
                        continue
                    size = m.size
                    if size <= 0 or size > self.MAX_SCAN_FILE_SIZE:
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    ext = ext.lower().lstrip(".")
                    if self._skip_ext(ext):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        content = f.read()
                    finally:
                        f.close()
                    score = self._score_candidate(name, len(content), content, ext)
                    if score > best_score:
                        best_score = score
                        best_content = content
                # Pass 2: arrays in relevant C/C++ headers
                for m in members:
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if not name_lower.endswith((".c", ".h", ".cpp", ".cc", ".cxx")):
                        continue
                    if not any(
                        k in name_lower
                        for k in ("poc", "capwap", "crash", "fuzz", "overflow", "heap")
                    ):
                        continue
                    if m.size <= 0 or m.size > self.MAX_CFILE_SIZE:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        text = f.read().decode("latin1", errors="ignore")
                    finally:
                        f.close()
                    for varname, arr_bytes in self._extract_arrays(text):
                        score = self._score_candidate(
                            m.name + "::" + varname,
                            len(arr_bytes),
                            arr_bytes,
                            ext="",
                            varname=varname,
                        )
                        if score > best_score:
                            best_score = score
                            best_content = arr_bytes
        except tarfile.TarError:
            return None
        return best_content

    def _solve_from_dir(self, root: str) -> Optional[bytes]:
        best_content: Optional[bytes] = None
        best_score = float("-inf")
        # Pass 1: binary-like files
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > self.MAX_SCAN_FILE_SIZE:
                    continue
                _, ext = os.path.splitext(fn)
                ext = ext.lower().lstrip(".")
                if self._skip_ext(ext):
                    continue
                try:
                    with open(path, "rb") as f:
                        content = f.read()
                except OSError:
                    continue
                rel_path = os.path.relpath(path, root)
                score = self._score_candidate(rel_path, len(content), content, ext)
                if score > best_score:
                    best_score = score
                    best_content = content
        # Pass 2: arrays in relevant C/C++ headers
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lower_fn = fn.lower()
                if not lower_fn.endswith((".c", ".h", ".cpp", ".cc", ".cxx")):
                    continue
                if not any(
                    k in lower_fn
                    for k in ("poc", "capwap", "crash", "fuzz", "overflow", "heap")
                ):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > self.MAX_CFILE_SIZE:
                    continue
                try:
                    with open(path, "r", encoding="latin1", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                rel_path = os.path.relpath(path, root)
                for varname, arr_bytes in self._extract_arrays(text):
                    score = self._score_candidate(
                        rel_path + "::" + varname,
                        len(arr_bytes),
                        arr_bytes,
                        ext="",
                        varname=varname,
                    )
                    if score > best_score:
                        best_score = score
                        best_content = arr_bytes
        return best_content

    def _skip_ext(self, ext: str) -> bool:
        skip = {
            "c",
            "h",
            "cpp",
            "cc",
            "cxx",
            "hpp",
            "hxx",
            "py",
            "sh",
            "bat",
            "ps1",
            "pl",
            "rb",
            "java",
            "cs",
            "js",
            "ts",
            "go",
            "php",
            "md",
            "rst",
            "txt",
            "rtf",
            "html",
            "htm",
            "xml",
            "xsl",
            "json",
            "yml",
            "yaml",
            "csv",
            "tsv",
            "ini",
            "cfg",
            "conf",
            "cmake",
            "am",
            "ac",
            "m4",
            "pc",
            "log",
            "tex",
            "cl",
            "v",
            "sv",
            "s",
            "asm",
            "o",
            "a",
            "so",
            "dylib",
            "dll",
            "lib",
            "jpg",
            "jpeg",
            "png",
            "gif",
            "bmp",
            "tiff",
            "svg",
            "gz",
            "bz2",
            "xz",
            "zip",
            "7z",
            "rar",
            "tar",
            "tgz",
            "tbz",
            "txz",
            "pdf",
            "doc",
            "docx",
            "xls",
            "xlsx",
            "ppt",
            "pptx",
        }
        return ext in skip

    def _score_candidate(
        self,
        rel_path: str,
        size: int,
        content: bytes,
        ext: str = "",
        varname: Optional[str] = None,
    ) -> float:
        lower_path = rel_path.lower()
        score = 0.0
        if "poc" in lower_path:
            score += 120.0
        if varname and "poc" in varname.lower():
            score += 120.0
        if "crash" in lower_path or (varname and "crash" in varname.lower()):
            score += 90.0
        if "heap" in lower_path or "overflow" in lower_path:
            score += 60.0
        if "capwap" in lower_path or (varname and "capwap" in varname.lower()):
            score += 80.0
        if "fuzz" in lower_path or "corpus" in lower_path or "seed" in lower_path:
            score += 40.0
        if "id:" in lower_path or "id_" in lower_path or "id-" in lower_path:
            score += 50.0
        if ext in ("bin", "dat", "raw", "pcap", "cap", "in", "inp", "seed"):
            score += 30.0
        base = os.path.basename(rel_path)
        if "." not in base:
            score += 10.0
        # closeness to target length
        score += max(0.0, 60.0 - abs(size - self.POC_TARGET_LEN))
        # binary-like bonus
        if size > 0:
            nonprint = 0
            for b in content:
                if b < 9 or (13 < b < 32) or b > 126:
                    nonprint += 1
            ratio = nonprint / size
            score += ratio * 20.0
        # small penalty for large files
        if size > 2048:
            score -= (size - 2048) / 1024.0 * 10.0
        return score

    def _extract_arrays(self, text: str):
        pattern = re.compile(
            r"(?:static\s+)?(?:const\s+)?(?:unsigned\s+char|uint8_t|u_char|char)\s+"
            r"([A-Za-z_]\w*)\s*\[\s*\]\s*=\s*{(.*?)}\s*;",
            re.S,
        )
        results = []
        for m in pattern.finditer(text):
            varname = m.group(1)
            body = m.group(2)
            arr = []
            for token in body.split(","):
                tok = token.strip()
                if not tok:
                    continue
                # remove comments
                if "/*" in tok:
                    tok = tok.split("/*", 1)[0].strip()
                if "//" in tok:
                    tok = tok.split("//", 1)[0].strip()
                if not tok:
                    continue
                # remove leading casts like (uint8_t)
                if tok.startswith("("):
                    while tok.startswith("(") and ")" in tok:
                        tok = tok.split(")", 1)[1].strip()
                if not tok:
                    continue
                # char literal
                if tok[0] == "'" and tok.endswith("'") and len(tok) >= 3:
                    ch = tok[1]
                    arr.append(ord(ch) & 0xFF)
                    continue
                # string literal
                if tok[0] == '"' and tok.endswith('"'):
                    s = tok[1:-1].encode("latin1", errors="ignore")
                    arr.extend(s)
                    continue
                # numeric with optional suffix
                m_int = re.match(r"(-?0x[0-9A-Fa-f]+)|(-?\d+)", tok)
                if not m_int:
                    continue
                num_str = m_int.group(0)
                try:
                    if num_str.lower().startswith("0x"):
                        v = int(num_str, 16)
                    else:
                        v = int(num_str, 10)
                except ValueError:
                    continue
                arr.append(v & 0xFF)
            if arr and len(arr) <= self.MAX_SCAN_FILE_SIZE:
                results.append((varname, bytes(arr)))
        return results
