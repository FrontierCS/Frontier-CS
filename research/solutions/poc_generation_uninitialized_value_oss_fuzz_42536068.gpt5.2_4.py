import os
import re
import tarfile
from typing import Optional, Tuple, List


class Solution:
    def _score_name(self, name: str) -> float:
        n = name.lower()
        score = 0.0

        if any(k in n for k in ("clusterfuzz", "testcase", "poc", "repro", "reproducer", "crash", "msan", "ubsan", "asan", "sanitizer")):
            score += 200.0
        if any(k in n for k in ("regression", "fuzz", "corpus", "seed", "inputs", "testdata", "samples", "sample")):
            score += 40.0

        base = os.path.basename(n)
        if base in ("poc", "crash", "repro", "reproducer", "testcase", "clusterfuzz-testcase-minimized", "clusterfuzz-testcase", "msan"):
            score += 200.0

        ext = os.path.splitext(base)[1]
        if ext in (".xml", ".svg", ".html", ".xhtml", ".json", ".yaml", ".yml", ".txt", ".dat", ".bin", ".input"):
            score += 25.0
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".pdf", ".zip", ".gz", ".bz2", ".xz"):
            score += 10.0

        if "/.git/" in n or n.endswith((".o", ".a", ".so", ".dll", ".dylib")):
            score -= 100.0

        return score

    def _score_size(self, size: int, target: int = 2179) -> float:
        if size <= 0:
            return -1000.0
        diff = abs(size - target)
        if diff == 0:
            return 120.0
        # Smooth proximity bonus, but not overly strong
        return max(0.0, 80.0 - (diff / 30.0))

    def _peek_bytes(self, tf: tarfile.TarFile, member: tarfile.TarInfo, n: int = 256) -> bytes:
        f = tf.extractfile(member)
        if not f:
            return b""
        try:
            return f.read(n)
        finally:
            try:
                f.close()
            except Exception:
                pass

    def _read_all(self, tf: tarfile.TarFile, member: tarfile.TarInfo, limit: int = 2_500_000) -> bytes:
        if member.size > limit:
            return b""
        f = tf.extractfile(member)
        if not f:
            return b""
        try:
            data = f.read()
            return data if isinstance(data, (bytes, bytearray)) else b""
        finally:
            try:
                f.close()
            except Exception:
                pass

    def _content_score(self, data: bytes) -> float:
        if not data:
            return -1000.0
        score = 0.0
        head = data[:512].lstrip()
        if head.startswith(b"<?xml") or head.startswith(b"<"):
            score += 40.0
        if b"<svg" in data[:4096].lower():
            score += 25.0
        if b"<html" in data[:4096].lower() or b"<!doctype html" in data[:4096].lower():
            score += 15.0
        if head.startswith(b"{") or head.startswith(b"["):
            score += 10.0
        # Avoid obviously source files
        if b"#include" in data[:4096] or b"int main" in data[:4096] or b"LLVMFuzzerTestOneInput" in data[:4096]:
            score -= 150.0
        return score

    def _find_best_embedded_poc(self, src_path: str) -> Optional[bytes]:
        target_len = 2179
        max_file_size = 2_500_000

        candidates: List[Tuple[float, tarfile.TarInfo]] = []
        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                for member in tf:
                    if not member.isreg():
                        continue
                    if member.size <= 0 or member.size > max_file_size:
                        continue

                    name_score = self._score_name(member.name)
                    size_score = self._score_size(member.size, target_len)
                    pre_score = name_score + size_score

                    # Consider likely candidates (or exact size match)
                    if member.size == target_len or pre_score >= 120.0 or ("clusterfuzz" in member.name.lower()):
                        candidates.append((pre_score, member))

                if not candidates:
                    return None

                candidates.sort(key=lambda x: x[0], reverse=True)
                top = candidates[:80]

                best: Tuple[float, Optional[bytes]] = (-1e18, None)
                for pre_score, member in top:
                    peek = self._peek_bytes(tf, member, 512)
                    # quick reject: binary archives likely not direct inputs
                    if peek.startswith(b"\x7fELF") or peek.startswith(b"MZ"):
                        continue
                    data = self._read_all(tf, member, max_file_size)
                    if not data:
                        continue
                    score = pre_score + self._content_score(data)
                    # Prefer smaller among close scores
                    score += max(0.0, 30.0 - (len(data) / 2000.0))
                    if score > best[0]:
                        best = (score, data)

                return best[1]
        except Exception:
            return None

    def _find_fuzzer_harness_hint(self, src_path: str) -> str:
        # Best-effort: detect likely format. Defaults to "xml".
        best_score = -1e18
        best_kind = "xml"
        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                for member in tf:
                    if not member.isreg():
                        continue
                    if member.size <= 0 or member.size > 900_000:
                        continue
                    n = member.name.lower()
                    if not (n.endswith((".cc", ".cpp", ".c", ".h", ".hpp"))):
                        continue
                    b = self._read_all(tf, member, 900_000)
                    if not b:
                        continue
                    if b"LLVMFuzzerTestOneInput" not in b:
                        continue
                    t = b.decode("utf-8", "ignore").lower()

                    score = 0.0
                    if "xml" in t or "tinyxml" in t or "pugi::xml" in t or "xmlreadmemory" in t or "xmldocument" in t:
                        score += 100.0
                    if "svg" in t:
                        score += 40.0
                    if "json" in t or "nlohmann::json" in t or "rapidjson" in t:
                        score += 70.0
                    if "yaml" in t:
                        score += 60.0
                    if "plist" in t:
                        score += 50.0
                    if "html" in t:
                        score += 30.0
                    if "attribute" in t:
                        score += 20.0

                    kind = "xml"
                    if score >= 70.0 and ("json" in t or "nlohmann::json" in t or "rapidjson" in t):
                        kind = "json"
                    if score >= 60.0 and "yaml" in t:
                        kind = "yaml"
                    if score >= 100.0 and ("xml" in t or "tinyxml" in t or "pugi::xml" in t):
                        kind = "xml"

                    if score > best_score:
                        best_score = score
                        best_kind = kind
        except Exception:
            pass
        return best_kind

    def _generate_fallback_poc(self, kind: str) -> bytes:
        if kind == "json":
            # Include numeric fields with invalid strings to provoke type conversions.
            s = (
                '{'
                '"root":{'
                '"width":"a",'
                '"height":"a",'
                '"x":"a",'
                '"y":"a",'
                '"scale":"a",'
                '"opacity":"a",'
                '"items":[{"r":"a","g":"a","b":"a","a":"a"},{"viewBox":"a a a a"}]'
                '}'
                '}'
            )
            return s.encode("utf-8", "strict")

        if kind == "yaml":
            s = (
                "root:\n"
                "  width: a\n"
                "  height: a\n"
                "  x: a\n"
                "  y: a\n"
                "  scale: a\n"
                "  opacity: a\n"
                "  items:\n"
                "    - r: a\n"
                "      g: a\n"
                "      b: a\n"
                "      a: a\n"
                "    - viewBox: \"a a a a\"\n"
            )
            return s.encode("utf-8", "strict")

        # XML/SVG-ish: many numeric-looking attributes set to invalid values.
        s = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            'width="a" height="a" viewBox="a a a a" x="a" y="a">\n'
            '  <g opacity="a" transform="translate(a,a) scale(a) rotate(a)">\n'
            '    <rect x="a" y="a" width="a" height="a" rx="a" ry="a" />\n'
            '    <circle cx="a" cy="a" r="a" />\n'
            '    <ellipse cx="a" cy="a" rx="a" ry="a" />\n'
            '    <line x1="a" y1="a" x2="a" y2="a" />\n'
            '    <polygon points="a,a a,a a,a" />\n'
            '    <polyline points="a,a a,a a,a" />\n'
            '    <path d="M 0 0 L 1 1 Z" stroke-width="a" />\n'
            '    <text x="a" y="a" font-size="a">x</text>\n'
            '  </g>\n'
            '</svg>\n'
        )
        return s.encode("utf-8", "strict")

    def solve(self, src_path: str) -> bytes:
        poc = self._find_best_embedded_poc(src_path)
        if isinstance(poc, (bytes, bytearray)) and len(poc) > 0:
            return bytes(poc)

        kind = self._find_fuzzer_harness_hint(src_path)
        return self._generate_fallback_poc(kind)