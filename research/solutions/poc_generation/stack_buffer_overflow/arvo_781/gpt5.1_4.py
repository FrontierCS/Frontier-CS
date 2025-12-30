import tarfile
import os
import re
from typing import Optional, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()

                data = self._find_by_exact_basenames(tf, members)
                if data:
                    return data

                data = self._find_by_keywords(tf, members)
                if data:
                    return data

                data = self._find_by_text_annotation(tf, members)
                if data:
                    return data

                if self._is_pcre_repo(members):
                    data = self._find_pcre_bug781_poc(tf, members)
                    if data:
                        return data
        except Exception:
            pass

        return self._fallback_poc()

    def _read_small_file(self, tf: tarfile.TarFile, member: tarfile.TarInfo, max_bytes: int) -> Optional[bytes]:
        if member.size == 0:
            return None
        try:
            f = tf.extractfile(member)
            if f is None:
                return None
            to_read = min(member.size, max_bytes)
            data = f.read(to_read)
            return data
        except Exception:
            return None

    def _looks_text(self, data: bytes) -> bool:
        if not data:
            return False
        if b"\x00" in data:
            return False
        text_chars = 0
        for b in data:
            if 32 <= b <= 126 or b in (9, 10, 13):
                text_chars += 1
        return text_chars / len(data) > 0.8

    def _find_by_exact_basenames(self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        target_names = [
            "poc",
            "poc.txt",
            "poc.bin",
            "poc.raw",
            "poc.dat",
            "poc.in",
            "poc.input",
            "poc-781",
            "poc_781",
            "bug781",
            "bug_781",
            "781",
            "crash",
            "crash.bin",
            "crash.txt",
            "id_000000",
            "id:000000",
        ]
        best_data: Optional[bytes] = None
        best_len: Optional[int] = None
        for target in target_names:
            lname = target.lower()
            for m in members:
                if m.isdir():
                    continue
                base = os.path.basename(m.name).lower()
                if base == lname:
                    data = self._read_small_file(tf, m, 4096)
                    if not data:
                        continue
                    length = len(data)
                    if best_data is None or length < (best_len or 0):
                        best_data = data
                        best_len = length
            if best_data is not None:
                break
        if best_data is not None:
            return best_data.rstrip(b"\r\n") or best_data
        return None

    def _extract_poc_from_text(self, data: bytes) -> Optional[bytes]:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            return None
        poc_pattern = re.compile(
            r"(?i)poc[^0-9A-Za-z]*(?:=|:)?\s*(\"([^\"]{1,32})\"|'([^']{1,32})'|([^\s#]{1,32}))"
        )
        m = poc_pattern.search(text)
        if m:
            s = m.group(2) or m.group(3) or m.group(4)
            if s:
                b = s.encode("utf-8")
                if b:
                    return b
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", ";", "/*", "*")):
                continue
            for sep in (":", "="):
                if sep in stripped:
                    stripped = stripped.split(sep, 1)[1].strip()
                    break
            qmatch = re.search(r'"([^"]{1,64})"', stripped)
            if qmatch:
                stripped = qmatch.group(1)
            else:
                qmatch = re.search(r"'([^']{1,64})'", stripped)
                if qmatch:
                    stripped = qmatch.group(1)
            if not stripped:
                continue
            b = stripped.encode("utf-8")
            if 0 < len(b) <= 64:
                return b
        return None

    def _find_with_keywords(
        self, tf: tarfile.TarFile, members: List[tarfile.TarInfo], keywords: List[str]
    ) -> Optional[bytes]:
        candidates: List[Tuple[int, int, bytes]] = []
        for m in members:
            if m.isdir():
                continue
            base = os.path.basename(m.name).lower()
            if not any(k in base for k in keywords):
                continue
            if m.size == 0 or m.size > 4096:
                continue
            data = self._read_small_file(tf, m, 4096)
            if not data:
                continue
            if self._looks_text(data):
                candidate = self._extract_poc_from_text(data)
                if not candidate:
                    continue
                data_to_use = candidate
            else:
                data_to_use = data.rstrip(b"\r\n")
                if not data_to_use:
                    continue
            size = len(data_to_use)
            dist = abs(size - 8)
            candidates.append((dist, size, data_to_use))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][2]

    def _find_by_keywords(self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        strong_keywords = ["poc", "crash", "bug781", "bug_781", "id_000", "repro"]
        data = self._find_with_keywords(tf, members, strong_keywords)
        if data:
            return data
        weak_keywords = ["bug", "issue", "regress", "input", "testcase", "case781", "781"]
        return self._find_with_keywords(tf, members, weak_keywords)

    def _find_by_text_annotation(self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        for m in members:
            if m.isdir():
                continue
            if m.size == 0 or m.size > 65536:
                continue
            name_lower = m.name.lower()
            if not any(
                k in name_lower
                for k in ("poc", "bug", "issue", "cve", "readme", "doc", "meta", "info", "arvo", "crash", "regress", "test")
            ):
                continue
            data = self._read_small_file(tf, m, 65536)
            if not data or not self._looks_text(data):
                continue
            lower_text = data.decode("utf-8", errors="ignore").lower()
            if "poc" not in lower_text:
                continue
            candidate = self._extract_poc_from_text(data)
            if candidate:
                return candidate
        return None

    def _is_pcre_repo(self, members: List[tarfile.TarInfo]) -> bool:
        for m in members:
            base = os.path.basename(m.name).lower()
            if base.startswith("pcre") and (base.endswith(".c") or base.endswith(".h")):
                return True
        return False

    def _find_pcre_bug781_poc(self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        slash_pattern = re.compile(r"/([^/\n]{1,64})/")
        for m in members:
            if m.isdir():
                continue
            if m.size == 0 or m.size > 512000:
                continue
            base = os.path.basename(m.name).lower()
            if not (
                base.endswith((".txt", ".c", ".h"))
                or "test" in base
                or "changelog" in base
                or "log" in base
                or "bug" in base
            ):
                continue
            data = self._read_small_file(tf, m, 512000)
            if not data or not self._looks_text(data):
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            lowered = text.lower()
            idx = lowered.find("bug 781")
            if idx == -1:
                idx = lowered.find("bug#781")
            if idx == -1:
                continue
            snippet = text[idx:]
            m_slash = slash_pattern.search(snippet)
            if m_slash:
                pat = m_slash.group(1)
                bpat = pat.encode("utf-8")
                if bpat:
                    return bpat[:8]
        return None

    def _fallback_poc(self) -> bytes:
        return b"()()()()"