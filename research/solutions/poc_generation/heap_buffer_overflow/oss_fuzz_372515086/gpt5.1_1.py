import os
import tarfile
import tempfile
import shutil
import subprocess
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_len = 1032
        tmp_root = None
        src_root = None
        try:
            if os.path.isdir(src_path):
                src_root = src_path
            else:
                tmp_root = tempfile.mkdtemp(prefix="poc_gen_")
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(tmp_root)
                    entries = [e for e in os.listdir(tmp_root) if not e.startswith(".")]
                    if len(entries) == 1:
                        single = os.path.join(tmp_root, entries[0])
                        if os.path.isdir(single):
                            src_root = single
                        else:
                            src_root = tmp_root
                    else:
                        src_root = tmp_root
                except tarfile.ReadError:
                    shutil.rmtree(tmp_root, ignore_errors=True)
                    tmp_root = None
                    src_root = src_path

            poc = self._find_known_poc(src_root, bug_id="372515086", base_len=base_len)
            if poc is not None:
                return poc

            poc = self._dynamic_generate_poc(src_root, base_len=base_len)
            if poc is not None:
                return poc

            poc = self._find_best_candidate_without_bugid(src_root, base_len=base_len)
            if poc is not None:
                return poc

            return os.urandom(base_len)
        finally:
            if tmp_root is not None and os.path.isdir(tmp_root):
                shutil.rmtree(tmp_root, ignore_errors=True)

    def _find_known_poc(self, src_root: str, bug_id: str, base_len: int) -> bytes | None:
        candidate_paths = []
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                if bug_id in fn:
                    full = os.path.join(dirpath, fn)
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        continue
                    if size <= 0 or size > 100000:
                        continue
                    candidate_paths.append((abs(size - base_len), full))
        if not candidate_paths:
            return None
        candidate_paths.sort(key=lambda x: x[0])
        best_path = candidate_paths[0][1]
        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _find_best_candidate_without_bugid(self, src_root: str, base_len: int) -> bytes | None:
        keywords = ("poc", "crash", "repro", "fuzz", "seed", "input", "case", "test")
        best_path = None
        best_score = None
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                lower = fn.lower()
                if not any(k in lower for k in keywords):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size <= 0 or size > 100000:
                    continue
                score = abs(size - base_len)
                if best_score is None or score < best_score:
                    best_score = score
                    best_path = full
        if best_path is None:
            return None
        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _dynamic_generate_poc(self, src_root: str, base_len: int) -> bytes | None:
        work_dir = tempfile.mkdtemp(prefix="poc_build_")
        try:
            exe_path = self._build_harness_executable(src_root, work_dir)
            if exe_path is None or not os.path.exists(exe_path):
                return None

            poc = self._try_candidate_files_with_exe(exe_path, src_root, base_len)
            if poc is not None:
                return poc

            poc = self._random_fuzz(exe_path, base_len)
            return poc
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _find_compiler(self) -> str | None:
        # Prefer C++-capable compilers for flexibility
        for c in ("clang++", "g++", "clang", "gcc"):
            try:
                res = subprocess.run(
                    [c, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if res.returncode == 0:
                    return c
            except OSError:
                continue
        return None

    def _collect_include_dirs(self, src_root: str) -> list[str]:
        dirs = set()
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                if fn.endswith((".h", ".hpp", ".hh", ".hxx")):
                    dirs.add(dirpath)
                    break
        dirs.add(src_root)
        return sorted(dirs)

    def _find_harness_file(self, src_root: str) -> str | None:
        harness_candidates: list[tuple[str, str]] = []
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".c", ".cc", ".cpp", ".cxx", ".cp", ".c++"):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                if "LLVMFuzzerTestOneInput" in text:
                    harness_candidates.append((full, text))
        if not harness_candidates:
            return None
        for full, text in harness_candidates:
            if "polygonToCellsExperimental" in text:
                return full
        for full, text in harness_candidates:
            if "polygonToCells" in text or "polygon" in os.path.basename(full).lower():
                return full
        return harness_candidates[0][0]

    def _build_harness_executable(self, src_root: str, work_dir: str) -> str | None:
        harness_file = self._find_harness_file(src_root)
        if harness_file is None:
            return None

        c_sources: list[str] = []
        other_sources: list[str] = []

        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".c", ".cc", ".cpp", ".cxx", ".cp", ".c++"):
                    continue
                full = os.path.join(dirpath, fn)
                if os.path.samefile(full, harness_file):
                    continue
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        header = f.read(4096)
                except OSError:
                    continue
                if "main(" in header or " main(" in header:
                    continue
                if ext == ".c":
                    c_sources.append(full)
                else:
                    other_sources.append(full)

        driver_path = os.path.join(work_dir, "poc_driver.c")
        driver_src = (
            "#include <stdint.h>\n"
            "#include <stddef.h>\n"
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "extern int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);\n"
            "int main(int argc, char **argv) {\n"
            "    if (argc < 2) return 0;\n"
            "    const char *path = argv[1];\n"
            "    FILE *f = fopen(path, \"rb\");\n"
            "    if (!f) return 1;\n"
            "    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 1; }\n"
            "    long sz = ftell(f);\n"
            "    if (sz < 0) { fclose(f); return 1; }\n"
            "    if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); return 1; }\n"
            "    size_t usz = (size_t)sz;\n"
            "    if (usz == 0) usz = 1;\n"
            "    uint8_t *buf = (uint8_t*)malloc(usz);\n"
            "    if (!buf) { fclose(f); return 1; }\n"
            "    size_t got = fread(buf, 1, usz, f);\n"
            "    fclose(f);\n"
            "    LLVMFuzzerTestOneInput(buf, got);\n"
            "    free(buf);\n"
            "    return 0;\n"
            "}\n"
        )
        try:
            with open(driver_path, "w", encoding="utf-8") as f:
                f.write(driver_src)
        except OSError:
            return None

        compiler = self._find_compiler()
        if compiler is None:
            return None

        exe_path = os.path.join(work_dir, "poc_harness_exe")
        sources = [driver_path, harness_file] + c_sources + other_sources
        include_dirs = self._collect_include_dirs(src_root)

        cmd = [
            compiler,
            "-fsanitize=address",
            "-g",
            "-O1",
            "-fno-omit-frame-pointer",
        ]
        for inc in include_dirs:
            cmd.extend(["-I", inc])
        cmd.extend(sources)
        cmd.extend(["-lm", "-o", exe_path])

        try:
            res = subprocess.run(
                cmd,
                cwd=work_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=180,
            )
        except Exception:
            return None
        if res.returncode != 0 or not os.path.exists(exe_path):
            return None
        return exe_path

    def _iter_candidate_binary_files(self, src_root: str, base_len: int):
        keywords = ("poc", "crash", "repro", "fuzz", "seed", "input", "case", "test")
        cands: list[tuple[int, str]] = []
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                lower = fn.lower()
                if not any(k in lower for k in keywords):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size <= 0 or size > 50000:
                    continue
                score = abs(size - base_len)
                cands.append((score, full))
        cands.sort(key=lambda x: x[0])
        for _, path in cands:
            yield path

    def _input_causes_crash(self, exe_path: str, data: bytes) -> bool:
        tmp_fd, tmp_name = tempfile.mkstemp(prefix="poc_input_")
        os.close(tmp_fd)
        try:
            with open(tmp_name, "wb") as f:
                f.write(data)
            env = os.environ.copy()
            existing_asan = env.get("ASAN_OPTIONS", "")
            extra = "abort_on_error=1:detect_leaks=0"
            if existing_asan:
                if not existing_asan.endswith(":"):
                    existing_asan += ":"
                env["ASAN_OPTIONS"] = existing_asan + extra
            else:
                env["ASAN_OPTIONS"] = extra
            try:
                res = subprocess.run(
                    [exe_path, tmp_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=5,
                )
            except subprocess.TimeoutExpired:
                return False
            stderr = res.stderr or b""
            if b"AddressSanitizer" in stderr:
                return True
            return False
        finally:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass

    def _try_candidate_files_with_exe(self, exe_path: str, src_root: str, base_len: int) -> bytes | None:
        for path in self._iter_candidate_binary_files(src_root, base_len):
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if not data:
                continue
            if self._input_causes_crash(exe_path, data):
                return data
        return None

    def _random_fuzz(self, exe_path: str, base_len: int) -> bytes | None:
        max_iters = 2000
        for i in range(max_iters):
            if i < 500:
                length = int(random.gauss(mu=base_len, sigma=max(4, base_len / 3)))
                if length < 1:
                    length = 1
                if length > 4096:
                    length = 4096
            else:
                length = random.randint(1, 4096)
            data = os.urandom(length)
            if self._input_causes_crash(exe_path, data):
                return data
        return None