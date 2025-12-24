import os
import re
import tarfile
from typing import Optional, Tuple


def _read_text_files_from_tar(tar_path: str, max_bytes_total: int = 8_000_000) -> str:
    out = []
    total = 0
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                name = m.name.lower()
                if not (name.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inc", ".inl", ".y", ".l", ".m4", ".am", ".ac", ".txt", ".md"))):
                    continue
                if total + m.size > max_bytes_total:
                    break
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                total += len(data)
                try:
                    out.append(data.decode("utf-8", errors="ignore"))
                except Exception:
                    continue
    except Exception:
        return ""
    return "\n".join(out)


def _read_text_files_from_dir(root: str, max_bytes_total: int = 8_000_000) -> str:
    out = []
    total = 0
    for base, _, files in os.walk(root):
        for fn in files:
            lfn = fn.lower()
            if not lfn.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inc", ".inl", ".y", ".l", ".m4", ".am", ".ac", ".txt", ".md")):
                continue
            path = os.path.join(base, fn)
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                if total + st.st_size > max_bytes_total:
                    return "\n".join(out)
                with open(path, "rb") as f:
                    data = f.read()
                total += len(data)
                out.append(data.decode("utf-8", errors="ignore"))
            except Exception:
                continue
    return "\n".join(out)


_CSTR_RE = re.compile(r'"((?:\\.|[^"\\])*)"')


def _unescape_c_string(s: str) -> str:
    if "\\" not in s:
        return s
    try:
        return bytes(s, "utf-8").decode("unicode_escape", errors="ignore")
    except Exception:
        return s


def _count_conversions(fmt: str) -> int:
    i = 0
    n = 0
    L = len(fmt)
    while i < L:
        if fmt[i] == "%":
            if i + 1 < L and fmt[i + 1] == "%":
                i += 2
                continue
            n += 1
            i += 1
            continue
        i += 1
    return n


def _find_best_scanf_format(all_text: str) -> Optional[str]:
    # Look for scanf-like format strings that contain a literal separator between two conversions.
    best = None
    best_score = None

    for m in _CSTR_RE.finditer(all_text):
        raw = m.group(1)
        if "%" not in raw:
            continue
        fmt = _unescape_c_string(raw)
        if fmt.count("%") < 2:
            continue

        # Prefer formats that explicitly include a dot between conversions
        # e.g. "%lld.%lld" or "%llu.%llu"
        if ".%" in fmt:
            score = (0, len(fmt))
        elif ",%" in fmt:
            score = (1, len(fmt))
        elif ":%" in fmt:
            score = (2, len(fmt))
        elif ";%" in fmt:
            score = (3, len(fmt))
        elif "/%" in fmt:
            score = (4, len(fmt))
        else:
            # Consider whitespace-separated formats (common in scanf)
            if re.search(r'%[^%"]+\s+%[^%"]+', fmt):
                score = (5, len(fmt))
            else:
                continue

        if best is None or score < best_score:
            best = fmt
            best_score = score

    return best


def _detect_separator_and_conversions(fmt: str) -> Tuple[str, int]:
    convs = _count_conversions(fmt)

    if ".%" in fmt:
        sep = "."
    elif ",%" in fmt:
        sep = ","
    elif ":%" in fmt:
        sep = ":"
    elif ";%" in fmt:
        sep = ";"
    elif "/%" in fmt:
        sep = "/"
    else:
        if re.search(r'%[^%"]+\s+%[^%"]+', fmt):
            sep = " "
        else:
            sep = "."
    return sep, convs


class Solution:
    def solve(self, src_path: str) -> bytes:
        all_text = ""
        if src_path and os.path.isdir(src_path):
            all_text = _read_text_files_from_dir(src_path)
        elif src_path and os.path.isfile(src_path):
            all_text = _read_text_files_from_tar(src_path)

        sep = "."
        convs = 2
        fmt = _find_best_scanf_format(all_text) if all_text else None
        if fmt:
            sep, convs = _detect_separator_and_conversions(fmt)

        # 19-digit max signed 64-bit value; avoids ERANGE for signed parsing while still long enough.
        num = "9223372036854775807"
        if sep == " ":
            base = f"{num} {num}"
        else:
            base = f"{num}{sep}{num}"

        extra = max(0, convs - 2)
        if extra:
            base += " " + " ".join(["0"] * extra)

        base += "\n"
        return base.encode("ascii", errors="ignore")