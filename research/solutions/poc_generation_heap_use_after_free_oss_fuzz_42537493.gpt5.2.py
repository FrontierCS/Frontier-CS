import os
import re
import tarfile
import tempfile
from typing import List, Tuple, Optional


def _safe_extract_tar(tar_path: str, dst_dir: str) -> str:
    with tarfile.open(tar_path, "r:*") as tf:
        dst_real = os.path.realpath(dst_dir)
        for m in tf.getmembers():
            name = m.name
            if not name or name == ".":
                continue
            out_path = os.path.join(dst_dir, name)
            out_real = os.path.realpath(out_path)
            if not (out_real == dst_real or out_real.startswith(dst_real + os.sep)):
                continue
            if m.isdir():
                os.makedirs(out_real, exist_ok=True)
                continue
            if not m.isreg():
                continue
            parent = os.path.dirname(out_real)
            if parent:
                os.makedirs(parent, exist_ok=True)
            f = tf.extractfile(m)
            if f is None:
                continue
            with f:
                with open(out_real, "wb") as w:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        w.write(chunk)
    # If a single top-level directory exists, return it; else return dst_dir
    try:
        entries = [e for e in os.listdir(dst_dir) if e not in (".", "..")]
    except OSError:
        return dst_dir
    if len(entries) == 1:
        p = os.path.join(dst_dir, entries[0])
        if os.path.isdir(p):
            return p
    return dst_dir


def _read_text_for_scan(path: str, max_bytes: int = 2 * 1024 * 1024) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
    except OSError:
        return ""
    try:
        return data.decode("utf-8", "ignore")
    except Exception:
        try:
            return data.decode("latin-1", "ignore")
        except Exception:
            return ""


def _walk_sources(root: str) -> List[str]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune some common huge dirs
        base = os.path.basename(dirpath)
        if base in (".git", ".svn", "node_modules", "venv", ".venv"):
            dirnames[:] = []
            continue
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() in exts:
                out.append(os.path.join(dirpath, fn))
    return out


def _score_fuzzer_source(txt: str, path: str) -> int:
    score = 0
    if "LLVMFuzzerTestOneInput" in txt:
        score += 1000
    if "Honggfuzz" in txt or "AFL" in txt:
        score += 100
    kw_weights = [
        ("xmlOutputBuffer", 60),
        ("xmlAllocOutputBuffer", 70),
        ("xmlOutputBufferCreate", 80),
        ("xmlSave", 50),
        ("xmlDocDump", 50),
        ("xmlTextWriter", 40),
        ("CharEncodingHandler", 40),
        ("xmlFindCharEncodingHandler", 80),
        ("xmlOpenCharEncodingHandler", 80),
        ("encoding", 10),
        ("io", 5),
    ]
    for kw, w in kw_weights:
        c = txt.count(kw)
        if c:
            score += min(30, c) * w
    low = os.path.basename(path).lower()
    if "io" in low:
        score += 50
    if "writer" in low:
        score += 30
    if "save" in low or "dump" in low:
        score += 30
    if "fuzz" in path.lower():
        score += 40
    return score


def _detect_parse_xml(txt: str) -> bool:
    pats = (
        "xmlReadMemory(",
        "xmlParseMemory(",
        "xmlCtxtReadMemory(",
        "htmlReadMemory(",
        "xmlReaderForMemory(",
        "xmlParseChunk(",
        "xmlReadDoc(",
        "xmlParseDoc(",
    )
    return any(p in txt for p in pats)


def _detect_serializer(txt: str) -> bool:
    pats = (
        "xmlDocDumpMemory",
        "xmlDocDumpFormatMemory",
        "xmlSaveToBuffer",
        "xmlSaveToIO",
        "xmlSaveDoc",
        "xmlSaveFile",
        "xmlSaveFormatFile",
        "xmlOutputBuffer",
        "xmlTextWriter",
    )
    return any(p in txt for p in pats)


def _detect_enc_handler_usage(txt: str) -> bool:
    pats = (
        "xmlFindCharEncodingHandler",
        "xmlOpenCharEncodingHandler",
        "xmlNewCharEncodingHandler",
        "xmlParseCharEncoding",
        "xmlCharEncodingHandler",
    )
    return any(p in txt for p in pats)


def _detect_nul_unsafe(txt: str) -> bool:
    # Very conservative: if any likely C-string usage on input path exists, avoid embedded NULs.
    if "xmlParseDoc(" in txt or "xmlReadDoc(" in txt:
        return True
    cstr_funcs = (
        "strlen(",
        "strdup(",
        "strndup(",
        "strcpy(",
        "strncpy(",
        "strcmp(",
        "strstr(",
        "strchr(",
        "strrchr(",
        "strtok(",
        "sscanf(",
    )
    if any(f in txt for f in cstr_funcs):
        return True
    # C++: constructing std::string from a char* without explicit length
    if re.search(r"std::string\s*\(\s*\(const\s+char\s*\*\)\s*data\s*\)", txt):
        return True
    if re.search(r"std::string\s+\w+\s*\(\s*\(const\s+char\s*\*\)\s*data\s*\)", txt):
        return True
    if re.search(r"std::string\s+\w+\s*=\s*\(const\s+char\s*\*\)\s*data\s*;", txt):
        return True
    return False


def _detect_encoding_separator(txt: str) -> bytes:
    # Heuristic: look for NUL-splitting or newline-splitting
    if "memchr" in txt and ("'\\0'" in txt or "\\0" in txt or "0x00" in txt):
        return b"\x00"
    if "'\\0'" in txt or '"\\0"' in txt or "\\0" in txt:
        return b"\x00"
    if "ConsumeLine" in txt or "'\\n'" in txt or '"\\n"' in txt:
        return b"\n"
    if "getline" in txt:
        return b"\n"
    return b"\x00"


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            if os.path.isdir(src_path):
                root = src_path
            else:
                root = _safe_extract_tar(src_path, td)

            srcs = _walk_sources(root)
            candidates: List[Tuple[int, str, str]] = []
            for p in srcs:
                txt = _read_text_for_scan(p)
                if not txt:
                    continue
                if "LLVMFuzzerTestOneInput" in txt or "fuzzer" in p.lower():
                    candidates.append((_score_fuzzer_source(txt, p), p, txt))

            if not candidates:
                # fallback: scan a limited set of sources for hints
                for p in srcs[:200]:
                    txt = _read_text_for_scan(p)
                    if not txt:
                        continue
                    candidates.append((_score_fuzzer_source(txt, p), p, txt))

            candidates.sort(key=lambda x: x[0], reverse=True)
            best_txt = candidates[0][2] if candidates else ""
            # Also aggregate top few candidates to reduce chance of choosing wrong fuzzer file
            agg = best_txt
            for _, _, t in candidates[1:5]:
                agg += "\n" + t

            parse_xml = _detect_parse_xml(agg)
            serializer = _detect_serializer(agg)
            enc_handler = _detect_enc_handler_usage(agg)
            nul_unsafe = _detect_nul_unsafe(agg)

            # Strategy 1: fuzzer directly exercises output buffers with encoding handler from input.
            if (
                enc_handler
                and (
                    ("xmlOutputBuffer" in agg)
                    or ("xmlAllocOutputBuffer" in agg)
                    or ("xmlSaveTo" in agg)
                )
                and not (parse_xml and not serializer)
            ):
                sep = _detect_encoding_separator(agg)
                # Use conversion-needed encoding; keep payload small.
                return b"UTF-16" + sep + b"<a/>"

            # Strategy 2: parse XML and serialize; use UTF-16 input to force encoder usage without verbose XML declaration.
            if parse_xml and serializer and not nul_unsafe:
                return b"\xff\xfe<\x00a\x00/\x00>\x00"

            # Strategy 3: parse XML and serialize, but input likely treated as C-string somewhere: avoid embedded NULs.
            if parse_xml and serializer and nul_unsafe:
                # Single-byte encoding compatible with ASCII; include a non-ASCII byte to ensure conversion path is exercised.
                return b"<?xml version='1.0' encoding='ISO-8859-1'?><a>\xa0</a>"

            # Fallbacks
            if parse_xml:
                return b"<a/>"
            return b"UTF-16\x00<a/>"
