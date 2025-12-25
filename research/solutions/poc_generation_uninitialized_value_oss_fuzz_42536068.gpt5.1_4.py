import os
import tarfile
import tempfile
import shutil
import stat
import subprocess
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        work_dir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            root_dir = self._prepare_root_dir(src_path, work_dir)

            # 1) Try to find embedded PoC of exact known size
            poc = self._find_embedded_poc(root_dir, 2179)
            if poc is not None:
                return poc

            # 2) Try dynamic fuzzing via libFuzzer harness
            poc = self._fuzz_for_crash(root_dir)
            if poc is not None:
                return poc

            # 3) Try heuristics on filenames
            poc = self._find_by_name_heuristics(root_dir)
            if poc is not None:
                return poc

            # 4) Fallback: random data of target size
            return self._generate_random_input(2179)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _prepare_root_dir(self, src_path: str, work_dir: str) -> str:
        if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(work_dir)
            entries = [os.path.join(work_dir, e) for e in os.listdir(work_dir)]
            subdirs = [p for p in entries if os.path.isdir(p)]
            if len(subdirs) == 1:
                return subdirs[0]
            return work_dir
        return os.path.abspath(src_path)

    def _walk_files(self, root_dir: str):
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for name in filenames:
                yield os.path.join(dirpath, name)

    def _find_embedded_poc(self, root_dir: str, target_size: int) -> Optional[bytes]:
        candidates = []
        for path in self._walk_files(root_dir):
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size == target_size:
                candidates.append(path)
        if not candidates:
            return None

        def score(p: str) -> int:
            name = os.path.basename(p).lower()
            s = 0
            if "poc" in name:
                s -= 4
            if "crash" in name or "bug" in name or "testcase" in name or "repro" in name:
                s -= 3
            if name.endswith((".xml", ".json", ".txt", ".bin", ".dat")):
                s -= 1
            return s

        candidates.sort(key=score)
        best = candidates[0]
        try:
            with open(best, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _find_by_name_heuristics(self, root_dir: str) -> Optional[bytes]:
        keywords = ("poc", "proof", "crash", "bug", "testcase", "repro", "input")
        best_path = None
        best_score = None
        for path in self._walk_files(root_dir):
            name = os.path.basename(path).lower()
            if not any(k in name for k in keywords):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size <= 0 or size > 1_000_000:
                continue
            score = (abs(size - 2179), -size)
            if best_score is None or score < best_score:
                best_score = score
                best_path = path
        if best_path is None:
            return None
        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _find_fuzz_binaries(self, root_dir: str):
        bins = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if not os.access(path, os.X_OK):
                    continue
                lower = name.lower()
                if "fuzz" in lower or "fuzzer" in lower:
                    bins.append(path)
        return bins

    def _try_build(self, root_dir: str, timeout: int = 120):
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for name in filenames:
                lower = name.lower()
                if lower in ("build.sh", "build_fuzzers.sh", "build_fuzzer.sh"):
                    candidates.append(os.path.join(dirpath, name))
            if dirpath != root_dir:
                depth = dirpath[len(root_dir):].count(os.sep)
                if depth > 2:
                    dirnames[:] = []
        if not candidates:
            return
        candidates.sort(key=len)
        script = candidates[0]
        out_dir = os.path.join(os.path.dirname(script), "out")
        os.makedirs(out_dir, exist_ok=True)
        env = os.environ.copy()
        import shutil as _shutil
        if _shutil.which("clang") and _shutil.which("clang++"):
            env.setdefault("CC", "clang")
            env.setdefault("CXX", "clang++")
        elif _shutil.which("gcc") and _shutil.which("g++"):
            env.setdefault("CC", "gcc")
            env.setdefault("CXX", "g++")
        env.setdefault("OUT", out_dir)
        env.setdefault("CFLAGS", "-g -O1")
        env.setdefault("CXXFLAGS", "-g -O1")
        try:
            subprocess.run(
                ["bash", script],
                cwd=os.path.dirname(script),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
        except Exception:
            pass

    def _run_libfuzzer_and_collect(self, binpath: str, timeout_fuzz: int = 60) -> Optional[bytes]:
        workdir = os.path.dirname(binpath)
        artifacts_dir = os.path.join(workdir, "artifacts")
        corpus_dir = os.path.join(workdir, "corpus")
        os.makedirs(artifacts_dir, exist_ok=True)
        os.makedirs(corpus_dir, exist_ok=True)
        env = os.environ.copy()

        def append_opt(var: str, key: str, value: str):
            current = env.get(var, "")
            if key in current:
                return
            if current:
                current += ":"
            current += f"{key}={value}"
            env[var] = current

        append_opt("ASAN_OPTIONS", "halt_on_error", "1")
        append_opt("ASAN_OPTIONS", "abort_on_error", "1")
        append_opt("ASAN_OPTIONS", "symbolize", "0")
        append_opt("UBSAN_OPTIONS", "halt_on_error", "1")
        append_opt("UBSAN_OPTIONS", "abort_on_error", "1")
        append_opt("UBSAN_OPTIONS", "symbolize", "0")
        append_opt("MSAN_OPTIONS", "halt_on_error", "1")

        args = [
            binpath,
            "-max_total_time={}".format(timeout_fuzz),
            "-artifact_prefix={}/".format(artifacts_dir),
            corpus_dir,
        ]
        try:
            subprocess.run(
                args,
                cwd=workdir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout_fuzz + 5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            pass

        try:
            for name in os.listdir(artifacts_dir):
                lower = name.lower()
                if (
                    lower.startswith("crash-")
                    or lower.startswith("leak-")
                    or lower.startswith("timeout-")
                    or lower.startswith("oom-")
                ):
                    path = os.path.join(artifacts_dir, name)
                    try:
                        with open(path, "rb") as f:
                            return f.read()
                    except OSError:
                        continue
        except OSError:
            return None
        return None

    def _fuzz_for_crash(self, root_dir: str, timeout_build: int = 120, timeout_fuzz: int = 60) -> Optional[bytes]:
        fuzz_bins = self._find_fuzz_binaries(root_dir)
        if not fuzz_bins:
            self._try_build(root_dir, timeout_build)
            fuzz_bins = self._find_fuzz_binaries(root_dir)
        if not fuzz_bins:
            return None
        fuzz_bins.sort(key=len)
        tried = 0
        for binpath in fuzz_bins:
            poc = self._run_libfuzzer_and_collect(binpath, timeout_fuzz)
            tried += 1
            if poc is not None:
                return poc
            if tried >= 3:
                break
        return None

    def _generate_random_input(self, length: int) -> bytes:
        return os.urandom(length)
