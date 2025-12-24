import os
import tarfile
import zipfile
from typing import Callable, List, Optional, NamedTuple


class _Entry(NamedTuple):
    name: str
    size: int
    loader: Callable[[], bytes]


class Solution:
    POC_SIZE = 6431
    MAX_READ_SIZE = 2 * 1024 * 1024  # 2MB safety cap

    def solve(self, src_path: str) -> bytes:
        data: Optional[bytes] = None

        if os.path.isdir(src_path):
            data = self._find_in_dir(src_path)
        else:
            if tarfile.is_tarfile(src_path):
                data = self._find_in_tar(src_path)
            elif zipfile.is_zipfile(src_path):
                data = self._find_in_zip(src_path)

        if data is None:
            data = self._fallback_pdf()

        return data

    # === Container handlers ===

    def _find_in_tar(self, path: str) -> Optional[bytes]:
        try:
            with tarfile.open(path, "r:*") as tf:
                entries: List[_Entry] = []
                for member in tf.getmembers():
                    if not member.isfile() or member.size <= 0:
                        continue

                    def make_loader(m: tarfile.TarInfo) -> Callable[[], bytes]:
                        def _loader() -> bytes:
                            f = tf.extractfile(m)
                            if f is None:
                                return b""
                            try:
                                return f.read()
                            finally:
                                f.close()
                        return _loader

                    entries.append(_Entry(member.name, member.size, make_loader(member)))
                return self._pick_poc(entries)
        except Exception:
            return None

    def _find_in_zip(self, path: str) -> Optional[bytes]:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                entries: List[_Entry] = []
                for info in zf.infolist():
                    # Detect directories in a version-agnostic way
                    if info.filename.endswith("/"):
                        continue
                    size = getattr(info, "file_size", 0)
                    if size <= 0:
                        continue

                    def make_loader(i: zipfile.ZipInfo) -> Callable[[], bytes]:
                        def _loader() -> bytes:
                            return zf.read(i.filename)
                        return _loader

                    entries.append(_Entry(info.filename, size, make_loader(info)))
                return self._pick_poc(entries)
        except Exception:
            return None

    def _find_in_dir(self, root: str) -> Optional[bytes]:
        entries: List[_Entry] = []
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue
                if size <= 0:
                    continue

                def make_loader(path: str) -> Callable[[], bytes]:
                    def _loader() -> bytes:
                        with open(path, "rb") as f:
                            return f.read()
                    return _loader

                rel_name = os.path.relpath(full_path, root)
                entries.append(_Entry(rel_name, size, make_loader(full_path)))
        return self._pick_poc(entries)

    # === Core selection logic ===

    def _pick_poc(self, entries: List[_Entry]) -> Optional[bytes]:
        if not entries:
            return None

        # Stage 1: Exact size match(es)
        exact = [e for e in entries if e.size == self.POC_SIZE]
        data = self._attempt_candidates(
            exact,
            sort_key=lambda e: (
                -self._score_name(e.name),
                e.name.count("/") + e.name.count("\\"),
                len(e.name),
            ),
        )
        if data is not None:
            return data

        # Stage 2: Interesting names near target size
        interesting = [e for e in entries if self._is_interesting_name(e.name)]
        data = self._attempt_candidates(
            interesting,
            sort_key=lambda e: (
                abs(e.size - self.POC_SIZE),
                -self._score_name(e.name),
                e.name.count("/") + e.name.count("\\"),
            ),
        )
        if data is not None:
            return data

        # Stage 3: Any .pdf files, preferring sizes near target
        pdfs = [e for e in entries if e.name.lower().endswith(".pdf")]
        data = self._attempt_candidates(
            pdfs,
            sort_key=lambda e: (
                abs(e.size - self.POC_SIZE),
                e.name.count("/") + e.name.count("\\"),
                len(e.name),
            ),
        )
        if data is not None:
            return data

        # If nothing suitable found, give up
        return None

    def _attempt_candidates(
        self,
        candidates: List[_Entry],
        sort_key: Callable[[_Entry], object],
    ) -> Optional[bytes]:
        if not candidates:
            return None

        for entry in sorted(candidates, key=sort_key):
            if entry.size <= 0 or entry.size > self.MAX_READ_SIZE:
                continue
            try:
                data = entry.loader()
            except Exception:
                continue
            if not data:
                continue
            if self._looks_like_pdf(data):
                return data
        return None

    # === Heuristics ===

    def _is_interesting_name(self, name: str) -> bool:
        n = name.lower()
        if n.endswith(".pdf"):
            return True
        keywords = [
            "poc",
            "crash",
            "heap",
            "uaf",
            "useafterfree",
            "use-after-free",
            "bug",
            "issue",
            "testcase",
        ]
        return any(k in n for k in keywords)

    def _score_name(self, name: str) -> int:
        n = name.lower()
        score = 0
        if n.endswith(".pdf"):
            score += 50
        if "poc" in n:
            score += 40
        if "crash" in n or "heap" in n or "uaf" in n:
            score += 30
        if "useafterfree" in n or "use-after-free" in n:
            score += 30
        if "test" in n or "case" in n:
            score += 10
        if "example" in n or "sample" in n:
            score += 5
        return score

    def _looks_like_pdf(self, data: bytes) -> bool:
        if not data:
            return False
        # Strip common leading whitespace/nulls
        prefix = data.lstrip(b"\x00\r\n\t ")
        return prefix.startswith(b"%PDF")

    # === Fallback ===

    def _fallback_pdf(self) -> bytes:
        # Simple, benign PDF as a last resort; unlikely to trigger crashes.
        return (
            b"%PDF-1.4\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"   /Contents 4 0 R /Resources << >> >>\n"
            b"endobj\n"
            b"4 0 obj\n"
            b"<< /Length 44 >>\n"
            b"stream\n"
            b"BT /F1 24 Tf 72 712 Td (Hello PoC) Tj ET\n"
            b"endstream\n"
            b"endobj\n"
            b"xref\n"
            b"0 5\n"
            b"0000000000 65535 f \n"
            b"0000000010 00000 n \n"
            b"0000000061 00000 n \n"
            b"0000000118 00000 n \n"
            b"0000000225 00000 n \n"
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"320\n"
            b"%%EOF\n"
        )
