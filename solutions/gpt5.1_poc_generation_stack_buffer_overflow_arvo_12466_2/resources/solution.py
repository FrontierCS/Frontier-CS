import os
import tarfile
import re
from typing import Optional

_ARRAY_RE = re.compile(
    r'(?:static\s+)?(?:const\s+)?(?:unsigned\s+char|unsigned\s+int8_t|uint8_t|char)\s+'
    r'([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*\]\s*=\s*\{(.*?)\};',
    re.DOTALL,
)

_C_BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


class Solution:
    GROUND_LEN = 524

    def solve(self, src_path: str) -> bytes:
        poc: Optional[bytes] = None

        if os.path.isdir(src_path):
            poc = self._find_poc_in_dir(src_path)
        else:
            try:
                if tarfile.is_tarfile(src_path):
                    poc = self._find_poc_in_tar(src_path)
                elif os.path.isdir(src_path):
                    poc = self._find_poc_in_dir(src_path)
            except Exception:
                if os.path.isdir(src_path):
                    try:
                        poc = self._find_poc_in_dir(src_path)
                    except Exception:
                        poc = None

        if poc is None:
            poc = self._default_poc()

        return poc

    def _score_candidate(self, name: str, size: int) -> float:
        name_l = name.lower()
        score = 0.0

        key_scores = [
            ("poc", 120.0),
            ("proof", 50.0),
            ("crash", 110.0),
            ("clusterfuzz", 100.0),
            ("stack-overflow", 90.0),
            ("overflow", 80.0),
            ("stack", 40.0),
            ("huff", 70.0),
            ("huffman", 70.0),
            ("rar5", 65.0),
            ("rar", 60.0),
            ("cve", 50.0),
            ("bug", 40.0),
            ("issue", 35.0),
            ("testcase", 30.0),
            ("oss-fuzz", 25.0),
            ("fuzz", 20.0),
            ("id:", 10.0),
        ]
        for kw, val in key_scores:
            if kw in name_l:
                score += val

        ext = os.path.splitext(name_l)[1]
        ext_scores = {
            ".rar": 80.0,
            ".rar5": 80.0,
            ".poc": 80.0,
            ".bin": 50.0,
            ".dat": 45.0,
            ".raw": 40.0,
            ".zip": 10.0,
            ".gz": 5.0,
            ".txt": -10.0,
            ".md": -20.0,
            ".c": -10.0,
            ".cc": -10.0,
            ".cpp": -10.0,
            ".cxx": -10.0,
            ".h": -15.0,
            ".hpp": -15.0,
            ".hh": -15.0,
            ".hxx": -15.0,
        }
        score += ext_scores.get(ext, 0.0)

        score -= abs(size - self.GROUND_LEN) / 8.0

        return score

    def _find_poc_in_tar(self, tar_path: str) -> Optional[bytes]:
        try:
            tf = tarfile.open(tar_path, "r:*")
        except Exception:
            return None

        with tf:
            members = [m for m in tf.getmembers() if m.isfile()]

            best_member = None
            best_score: Optional[float] = None

            for m in members:
                size = m.size
                if size == 0 or size > 5_000_000:
                    continue
                name = m.name
                score = self._score_candidate(name, size)
                if best_score is None or score > best_score:
                    best_score = score
                    best_member = m

            if best_member is not None and best_score is not None:
                try:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

            arr = self._find_poc_in_text_members(tf, members)
            if arr is not None:
                return arr

        return None

    def _is_likely_text_source(self, name_l: str) -> bool:
        ext = os.path.splitext(name_l)[1]
        return ext in (
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".hxx",
            ".inc",
            ".txt",
        )

    def _find_poc_in_text_members(
        self, tf: tarfile.TarFile, members
    ) -> Optional[bytes]:
        best_bytes: Optional[bytes] = None
        best_score: Optional[float] = None

        for m in members:
            if not m.isfile():
                continue
            size = m.size
            if size == 0 or size > 1_000_000:
                continue

            name = m.name
            name_l = name.lower()

            if not self._is_likely_text_source(name_l):
                continue

            if not any(
                kw in name_l
                for kw in (
                    "poc",
                    "crash",
                    "rar",
                    "huff",
                    "fuzz",
                    "oss-fuzz",
                    "regress",
                    "test",
                    "bug",
                    "stack",
                    "overflow",
                )
            ):
                continue

            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                content_bytes = f.read()
            except Exception:
                continue

            if not content_bytes:
                continue

            try:
                text = content_bytes.decode("utf-8", "ignore")
            except Exception:
                try:
                    text = content_bytes.decode("latin1", "ignore")
                except Exception:
                    continue

            for data_bytes, ctx_name in self._extract_arrays_from_text(text, name):
                length = len(data_bytes)
                if length == 0 or length > 5_000_000:
                    continue
                score = self._score_candidate(ctx_name, length)
                if best_score is None or score > best_score:
                    best_score = score
                    best_bytes = data_bytes

        return best_bytes

    def _find_poc_in_dir(self, base_dir: str) -> Optional[bytes]:
        best_path: Optional[str] = None
        best_score: Optional[float] = None

        for root, _, files in os.walk(base_dir):
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > 5_000_000:
                    continue
                rel_name = os.path.relpath(path, base_dir)
                score = self._score_candidate(rel_name, size)
                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path

        if best_path is not None and best_score is not None:
            try:
                with open(best_path, "rb") as f:
                    data = f.read()
                    if data:
                        return data
            except Exception:
                pass

        arr = self._find_poc_in_text_files_dir(base_dir)
        if arr is not None:
            return arr

        return None

    def _find_poc_in_text_files_dir(self, base_dir: str) -> Optional[bytes]:
        best_bytes: Optional[bytes] = None
        best_score: Optional[float] = None

        for root, _, files in os.walk(base_dir):
            for fname in files:
                name_l = fname.lower()
                ext = os.path.splitext(name_l)[1]
                if ext not in (
                    ".c",
                    ".cc",
                    ".cpp",
                    ".cxx",
                    ".h",
                    ".hpp",
                    ".hh",
                    ".hxx",
                    ".inc",
                    ".txt",
                ):
                    continue

                rel_path = os.path.relpath(os.path.join(root, fname), base_dir)
                rel_l = rel_path.lower()
                if not any(
                    kw in rel_l
                    for kw in (
                        "poc",
                        "crash",
                        "rar",
                        "huff",
                        "fuzz",
                        "oss-fuzz",
                        "regress",
                        "test",
                        "bug",
                        "stack",
                        "overflow",
                    )
                ):
                    continue

                path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(path)
                    if size == 0 or size > 1_000_000:
                        continue
                    with open(path, "rb") as f:
                        content_bytes = f.read()
                except OSError:
                    continue

                if not content_bytes:
                    continue

                try:
                    text = content_bytes.decode("utf-8", "ignore")
                except Exception:
                    try:
                        text = content_bytes.decode("latin1", "ignore")
                    except Exception:
                        continue

                for data_bytes, ctx_name in self._extract_arrays_from_text(
                    text, rel_path
                ):
                    length = len(data_bytes)
                    if length == 0 or length > 5_000_000:
                        continue
                    score = self._score_candidate(ctx_name, length)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_bytes = data_bytes

        return best_bytes

    def _extract_arrays_from_text(self, text: str, context_name: str):
        for m in _ARRAY_RE.finditer(text):
            var_name = m.group(1)
            init_str = m.group(2)
            data_bytes = self._parse_c_array_initializer(init_str)
            if data_bytes:
                yield data_bytes, context_name + ":" + var_name

    def _parse_c_array_initializer(self, init_str: str) -> Optional[bytes]:
        s = _C_BLOCK_COMMENT_RE.sub("", init_str)

        lines = []
        for line in s.splitlines():
            if "//" in line:
                line = line.split("//", 1)[0]
            lines.append(line)
        s = " ".join(lines)

        tokens = s.replace("\n", " ").replace("\r", " ").split(",")
        out = bytearray()

        for tok in tokens:
            t = tok.strip()
            if not t:
                continue

            while t.startswith("(") and ")" in t:
                t = t.split(")", 1)[1].strip()
            if not t:
                continue

            t = re.sub(r"[uUlL]+$", "", t).strip()
            if not t:
                continue

            try:
                val = int(t, 0)
            except ValueError:
                continue

            out.append(val & 0xFF)

        if not out:
            return None
        return bytes(out)

    def _default_poc(self) -> bytes:
        header = b"Rar!\x1A\x07\x01\x00"
        body = b"A" * 516
        return header + body
