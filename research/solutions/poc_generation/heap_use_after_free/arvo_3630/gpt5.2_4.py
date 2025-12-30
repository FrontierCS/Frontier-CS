import os
import re
import tarfile
from typing import Optional


class Solution:
    def _read_member_text(self, tf: tarfile.TarFile, member: tarfile.TarInfo) -> str:
        f = tf.extractfile(member)
        if not f:
            return ""
        data = f.read()
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            try:
                return data.decode("latin-1", errors="ignore")
            except Exception:
                return ""

    def _find_pj_lsat_text(self, src_path: str) -> str:
        if not os.path.isfile(src_path):
            return ""
        try:
            with tarfile.open(src_path, "r:*") as tf:
                candidates = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    base = os.path.basename(m.name)
                    if base == "PJ_lsat.c":
                        return self._read_member_text(tf, m)
                    if base.lower() == "pj_lsat.c":
                        candidates.append(m)
                if candidates:
                    return self._read_member_text(tf, candidates[0])
        except Exception:
            return ""
        return ""

    def _extract_proj_name(self, text: str) -> str:
        m = re.search(r'\bPROJ_HEAD\s*\(\s*([A-Za-z0-9_]+)\s*,', text)
        if m:
            return m.group(1)
        m = re.search(r'\bPROJECTION\s*\(\s*([A-Za-z0-9_]+)\s*\)', text)
        if m:
            return m.group(1)
        return "lsat"

    def _extract_param_names(self, text: str) -> set:
        params = set()
        for m in re.finditer(r'pj_param\s*\([^;]*,\s*"([^"]+)"\s*\)', text):
            spec = m.group(1)
            if not spec:
                continue
            # spec usually like: "ilsat", "ipath", "tsomeflag", "dlat_0", etc.
            # first char indicates type; remaining is param name
            if len(spec) >= 2:
                name = spec[1:]
                if re.fullmatch(r"[A-Za-z0-9_]+", name):
                    params.add(name)
        return params

    def _pick_param(self, params: set, prefer: str) -> Optional[str]:
        if prefer in params:
            return prefer
        for p in params:
            if prefer in p:
                return p
        return None

    def solve(self, src_path: str) -> bytes:
        text = self._find_pj_lsat_text(src_path)
        proj_name = self._extract_proj_name(text) if text else "lsat"
        params = self._extract_param_names(text) if text else set()

        lsat_param = self._pick_param(params, "lsat") or "lsat"
        path_param = self._pick_param(params, "path") or "path"

        # Intentionally invalid required parameters to hit error handling path
        # while providing a non-spherical ellipsoid to get past generic checks.
        s = f"+proj={proj_name} +{lsat_param}=0 +{path_param}=0 +a=2 +b=1"
        return s.encode("ascii", errors="ignore") + b"\x00"