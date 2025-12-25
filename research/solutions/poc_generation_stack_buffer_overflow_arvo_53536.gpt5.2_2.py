import os
import re
import tarfile
from collections import Counter
from typing import Iterable, Tuple, Optional


def _c_unescape_to_bytes(s: str) -> bytes:
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != '\\':
            out.append(ord(c) if ord(c) <= 0xFF else ord('?'))
            i += 1
            continue
        i += 1
        if i >= n:
            out.append(ord('\\'))
            break
        e = s[i]
        i += 1
        if e == 'n':
            out.append(0x0A)
        elif e == 'r':
            out.append(0x0D)
        elif e == 't':
            out.append(0x09)
        elif e == '0':
            j = i
            while j < n and j - i < 2 and s[j] in '01234567':
                j += 1
            oct_digits = s[i:j]
            if oct_digits:
                out.append(int('0' + oct_digits, 8) & 0xFF)
            else:
                out.append(0)
            i = j
        elif e == 'x':
            if i + 1 < n and all(ch in '0123456789abcdefABCDEF' for ch in s[i:i + 2]):
                out.append(int(s[i:i + 2], 16) & 0xFF)
                i += 2
            else:
                out.append(ord('x'))
        elif e in '01234567':
            j = i
            while j < n and j - i < 2 and s[j] in '01234567':
                j += 1
            oct_digits = e + s[i:j]
            out.append(int(oct_digits, 8) & 0xFF)
            i = j
        elif e == '\\':
            out.append(ord('\\'))
        elif e == '"':
            out.append(ord('"'))
        elif e == "'":
            out.append(ord("'"))
        elif e == 'a':
            out.append(0x07)
        elif e == 'b':
            out.append(0x08)
        elif e == 'f':
            out.append(0x0C)
        elif e == 'v':
            out.append(0x0B)
        else:
            out.append(ord(e) if ord(e) <= 0xFF else ord('?'))
    return bytes(out)


def _iter_source_texts(src_path: str) -> Iterable[Tuple[str, str]]:
    def should_read(path: str) -> bool:
        p = path.lower()
        if any(part in p for part in ("/.git/", "/.svn/", "/.hg/", "/build/", "/dist/", "/out/")):
            return False
        return p.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inc"))

    if os.path.isdir(src_path):
        for root, dirs, files in os.walk(src_path):
            dirs[:] = [d for d in dirs if d not in ('.git', '.svn', '.hg', 'build', 'dist', 'out')]
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, src_path)
                if not should_read("/" + rel.replace(os.sep, "/")):
                    continue
                try:
                    st = os.stat(full)
                    if st.st_size > 2_000_000:
                        continue
                    with open(full, "rb") as f:
                        data = f.read()
                    text = data.decode("utf-8", errors="ignore")
                    yield rel, text
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not should_read("/" + name):
                    continue
                if m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    text = data.decode("utf-8", errors="ignore")
                    yield name, text
                except Exception:
                    continue
    except Exception:
        return


def _choose_buf_size(candidates: Counter) -> int:
    plausible = [sz for sz, cnt in candidates.items() if 128 <= sz <= 4096 and cnt > 0]
    if not plausible:
        return 1024
    if 1024 in candidates:
        return 1024
    if 2048 in candidates:
        return 2048
    return max(plausible)


def _best_magic(magic_counter: Counter) -> Optional[bytes]:
    if not magic_counter:
        return None
    top = magic_counter.most_common(3)
    if not top:
        return None
    if len(top) == 1:
        cand_s, cand_n = top[0]
        if cand_n >= 2:
            b = _c_unescape_to_bytes(cand_s)
            if b and b.find(b"\x00") == -1 and all((9 <= x <= 13) or (32 <= x <= 126) for x in b):
                return b
        return None
    (s1, c1), (s2, c2) = top[0], top[1]
    if c1 < 2 or c1 < c2 + 2:
        return None
    b = _c_unescape_to_bytes(s1)
    if not b:
        return None
    if b.find(b"\x00") != -1:
        return None
    if not all((9 <= x <= 13) or (32 <= x <= 126) for x in b):
        return None
    return b


class Solution:
    def solve(self, src_path: str) -> bytes:
        syntax_scores = {
            "angle": 0,
            "curly": 0,
            "bracket": 0,
            "dollar": 0,
            "percent": 0,
        }
        buf_sizes = Counter()
        angle_tags = Counter()
        curly_tags = Counter()
        bracket_tags = Counter()
        generic_tags = Counter()
        magic_lits = Counter()

        re_char_lt = re.compile(r"'\s*<\s*'")
        re_char_gt = re.compile(r"'\s*>\s*'")
        re_char_lc = re.compile(r"'\s*\{\s*'")
        re_char_rc = re.compile(r"'\s*\}\s*'")
        re_char_lb = re.compile(r"'\s*\[\s*'")
        re_char_rb = re.compile(r"'\s*\]\s*'")
        re_char_dollar = re.compile(r"'\s*\$\s*'")
        re_char_percent = re.compile(r"'\s*%\s*'")

        re_char_arr = re.compile(r"\bchar\s+([A-Za-z_]\w*)\s*\[\s*(\d{2,5})\s*\]")
        re_define_num = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(\d{2,5})\b", re.M)
        re_angle_tag_in_lit = re.compile(r'"<\s*/?\s*([A-Za-z][A-Za-z0-9_-]{0,15})[^"]*?>"')
        re_curly_tag_in_lit = re.compile(r'"\{\{\s*([A-Za-z][A-Za-z0-9_-]{0,15})\s*\}\}"')
        re_bracket_tag_in_lit = re.compile(r'"\[\s*([A-Za-z][A-Za-z0-9_-]{0,15})\s*\]"')
        re_strcmp_tag = re.compile(r"\bstr(?:case)?cmp\s*\(\s*[^,]*tag[^,]*,\s*\"([A-Za-z][A-Za-z0-9_-]{0,31})\"\s*\)", re.I)
        re_memcmp_magic = re.compile(r"\bmem(?:cmp|casecmp)\s*\(\s*[^,]+,\s*\"([^\"]{2,32})\"\s*,\s*(\d{1,2})\s*\)")
        re_strncmp_magic = re.compile(r"\bstrn(?:cmp|casecmp)\s*\(\s*[^,]+,\s*\"([^\"]{2,32})\"\s*,\s*(\d{1,2})\s*\)")

        for _, text in _iter_source_texts(src_path):
            syntax_scores["angle"] += len(re_char_lt.findall(text)) + len(re_char_gt.findall(text))
            syntax_scores["curly"] += len(re_char_lc.findall(text)) + len(re_char_rc.findall(text)) + text.count("{{") + text.count("}}")
            syntax_scores["bracket"] += len(re_char_lb.findall(text)) + len(re_char_rb.findall(text))
            syntax_scores["dollar"] += len(re_char_dollar.findall(text)) + text.count("${") + text.count("$(")
            syntax_scores["percent"] += len(re_char_percent.findall(text)) + text.count("<%") + text.count("%>") + text.count("%{")

            for m in re_char_arr.finditer(text):
                var = m.group(1).lower()
                sz = int(m.group(2))
                if sz < 64 or sz > 65536:
                    continue
                if any(k in var for k in ("out", "output", "dst", "dest", "buf", "buffer")):
                    buf_sizes[sz] += 2
                else:
                    buf_sizes[sz] += 1

            for m in re_define_num.finditer(text):
                name = m.group(1).lower()
                sz = int(m.group(2))
                if 64 <= sz <= 65536 and any(k in name for k in ("out", "output", "buf", "buffer", "dst", "dest")):
                    buf_sizes[sz] += 2

            for m in re_angle_tag_in_lit.finditer(text):
                angle_tags[m.group(1).lower()] += 1
            for m in re_curly_tag_in_lit.finditer(text):
                curly_tags[m.group(1).lower()] += 1
            for m in re_bracket_tag_in_lit.finditer(text):
                bracket_tags[m.group(1).lower()] += 1
            for m in re_strcmp_tag.finditer(text):
                generic_tags[m.group(1).lower()] += 1

            for m in re_memcmp_magic.finditer(text):
                lit = m.group(1)
                n = int(m.group(2))
                if 2 <= n <= 16:
                    b = _c_unescape_to_bytes(lit)
                    if len(b) == n and b.find(b"\x00") == -1 and all((32 <= x <= 126) for x in b):
                        magic_lits[lit] += 1
            for m in re_strncmp_magic.finditer(text):
                lit = m.group(1)
                n = int(m.group(2))
                if 2 <= n <= 16:
                    b = _c_unescape_to_bytes(lit)
                    if len(b) == n and b.find(b"\x00") == -1 and all((32 <= x <= 126) for x in b):
                        magic_lits[lit] += 1

        buf_guess = _choose_buf_size(buf_sizes)

        syntax = max(syntax_scores.items(), key=lambda kv: kv[1])[0]
        if syntax_scores[syntax] == 0:
            syntax = "angle"

        tag_name = None
        if syntax == "angle":
            if angle_tags:
                tag_name = angle_tags.most_common(1)[0][0]
            elif generic_tags:
                tag_name = generic_tags.most_common(1)[0][0]
            else:
                tag_name = "a"
        elif syntax == "curly":
            if curly_tags:
                tag_name = curly_tags.most_common(1)[0][0]
            elif generic_tags:
                tag_name = generic_tags.most_common(1)[0][0]
            else:
                tag_name = "a"
        elif syntax == "bracket":
            if bracket_tags:
                tag_name = bracket_tags.most_common(1)[0][0]
            elif generic_tags:
                tag_name = generic_tags.most_common(1)[0][0]
            else:
                tag_name = "a"
        else:
            if generic_tags:
                tag_name = generic_tags.most_common(1)[0][0]
            else:
                tag_name = "a"

        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,15}", tag_name or ""):
            tag_name = "a"
        name_b = tag_name.encode("ascii", errors="ignore") or b"a"

        if syntax == "angle":
            unit = b"<" + name_b + b"></" + name_b + b">"
        elif syntax == "curly":
            unit = b"{{" + name_b + b"}}"
        elif syntax == "bracket":
            unit = b"[" + name_b + b"]"
        elif syntax == "dollar":
            unit = b"${" + name_b + b"}"
        else:
            unit = b"<" + name_b + b">"

        if len(unit) < 3:
            unit = b"<a>"

        target_len = max(1461, min(4096, buf_guess + 512))

        prefix = _best_magic(magic_lits)
        if prefix:
            if not prefix.endswith(b"\n"):
                prefix = prefix + b"\n"
        else:
            prefix = b""

        remaining = max(0, target_len - len(prefix))
        reps = (remaining + len(unit) - 1) // len(unit)
        payload = prefix + (unit * reps)
        if len(payload) < target_len:
            payload += unit
        payload = payload[:max(target_len, len(prefix) + len(unit))]
        if not payload.endswith(b"\n"):
            payload += b"\n"
        return payload