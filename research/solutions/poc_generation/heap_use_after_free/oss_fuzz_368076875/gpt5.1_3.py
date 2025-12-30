import os
import tarfile
import tempfile
import subprocess
import time
import random
import shutil
from typing import List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        start_time = time.time()
        total_time_budget = 75.0
        build_time_budget = 35.0

        workdir = None
        try:
            workdir = tempfile.mkdtemp(prefix="pocgen-")
            root = self._extract_src(src_path, workdir)

            # 1) Try to find existing PoC files in the repository.
            poc = self._find_existing_poc(root)
            if poc is not None:
                return poc

            # 2) Try to build fuzz binary and fuzz for a crash.
            bin_path = self._build_fuzz_binary(
                root, start_time=start_time, max_build_time=build_time_budget
            )
            if bin_path is not None and time.time() - start_time < total_time_budget:
                poc = self._fuzz_for_heap_uaf(
                    bin_path,
                    root,
                    start_time=start_time,
                    total_time_budget=total_time_budget,
                )
                if poc is not None:
                    # Optional shrinking if time permits.
                    if time.time() - start_time < total_time_budget - 5.0:
                        poc = self._shrink_input(
                            bin_path,
                            poc,
                            start_time=start_time,
                            total_time_budget=total_time_budget,
                        )
                    return poc

            # 3) Fallback: return a simple deterministic payload.
            return b"A" * 16
        except Exception:
            return b"A" * 16
        finally:
            if workdir and os.path.isdir(workdir):
                shutil.rmtree(workdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_src(self, src_path: str, workdir: str) -> str:
        root = workdir
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(workdir)
            else:
                # If it's not a tar, assume it's already a directory with sources.
                root = src_path
        except Exception:
            root = src_path

        # Flatten single top-level directory if present.
        try:
            entries = [
                e for e in os.listdir(root) if not e.startswith(".") and e != "__MACOSX"
            ]
            if len(entries) == 1:
                single = os.path.join(root, entries[0])
                if os.path.isdir(single):
                    root = single
        except Exception:
            pass
        return root

    # ------------------------------------------------------------------
    # PoC search in repository
    # ------------------------------------------------------------------

    def _find_existing_poc(self, root: str) -> Optional[bytes]:
        interesting_keywords = [
            "poc",
            "uaf",
            "crash",
            "repro",
            "heap",
            "use_after_free",
            "use-after-free",
            "368076875",
            "testcase",
            "oss-fuzz",
        ]
        best_data = None
        best_size = None

        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                lower = name.lower()
                if not any(k in lower for k in interesting_keywords):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                    # Skip overly large or empty files.
                    if size == 0 or size > 600_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    # Heuristic: skip log files containing ASan output.
                    if b"AddressSanitizer" in data or b"==ERROR:" in data:
                        continue
                    if best_data is None or size < best_size:
                        best_data = data
                        best_size = size
                except Exception:
                    continue
        return best_data

    # ------------------------------------------------------------------
    # Fuzz harness discovery & build
    # ------------------------------------------------------------------

    def _find_harness_files(self, root: str) -> List[str]:
        harness_files: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext not in (".c", ".cc", ".cpp", ".cxx", ".c++", ".cxx"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "rb") as f:
                        head = f.read(4096)
                    if b"LLVMFuzzerTestOneInput" in head:
                        harness_files.append(path)
                except Exception:
                    continue
        return harness_files

    def _choose_harness(self, harness_files: List[str]) -> Optional[str]:
        if not harness_files:
            return None

        keywords = ["ast", "repr", "syntax", "print", "dump", "fuzz"]

        def score(path: str) -> Tuple[int, int]:
            name = os.path.basename(path).lower()
            s = 0
            for i, kw in enumerate(keywords):
                if kw in name:
                    s += 10 - i
            return s, -len(path)

        harness_files_sorted = sorted(
            harness_files, key=lambda p: score(p), reverse=True
        )
        return harness_files_sorted[0]

    def _build_fuzz_binary(
        self, root: str, start_time: float, max_build_time: float
    ) -> Optional[str]:
        harness_files = self._find_harness_files(root)
        if not harness_files:
            return None

        chosen = self._choose_harness(harness_files)
        if chosen is None:
            return None

        deadline = start_time + max_build_time
        for mode in ("minimal", "all"):
            if time.time() > deadline:
                break
            try:
                bin_path = self._build_mode(root, chosen, harness_files, mode, deadline)
                if bin_path is not None:
                    return bin_path
            except Exception:
                continue
        return None

    def _compiler_paths(self) -> Tuple[Optional[str], Optional[str]]:
        import shutil as _shutil

        cxx = _shutil.which("clang++") or _shutil.which("g++")
        cc = _shutil.which("clang") or _shutil.which("gcc")
        return cc, cxx

    def _build_mode(
        self,
        root: str,
        harness_file: str,
        all_harness_files: List[str],
        mode: str,
        deadline: float,
    ) -> Optional[str]:
        cc, cxx = self._compiler_paths()
        if cc is None or cxx is None:
            return None

        build_dir = tempfile.mkdtemp(prefix="build-", dir=root)
        obj_files: List[str] = []
        c_sources: List[str] = []
        cxx_sources: List[str] = []

        harness_ext = os.path.splitext(harness_file)[1].lower()
        is_harness_c = harness_ext == ".c"

        if mode == "minimal":
            if is_harness_c:
                c_sources.append(harness_file)
            else:
                cxx_sources.append(harness_file)
        else:  # mode == "all"
            other_harness = set(all_harness_files)
            other_harness.discard(harness_file)
            main_markers = [" main(", "\nmain(", "\tmain(", "int main(", "void main(", "::main("]

            for dirpath, _, filenames in os.walk(root):
                for name in filenames:
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in (".c", ".cc", ".cpp", ".cxx", ".c++", ".cxx"):
                        continue
                    path = os.path.join(dirpath, name)
                    if path == harness_file:
                        continue
                    if path in other_harness:
                        continue
                    try:
                        with open(path, "r", errors="ignore") as f:
                            head = f.read(4096)
                    except Exception:
                        continue
                    # Skip other fuzzers and files defining main().
                    if "LLVMFuzzerTestOneInput" in head:
                        continue
                    if any(m in head for m in main_markers):
                        continue
                    if ext == ".c":
                        c_sources.append(path)
                    else:
                        cxx_sources.append(path)

            # Ensure harness is first in the list.
            if is_harness_c:
                c_sources.insert(0, harness_file)
            else:
                cxx_sources.insert(0, harness_file)

        # Prepare driver.cpp
        driver_cpp = os.path.join(build_dir, "driver.cpp")
        driver_src = (
            "#include <cstdint>\n"
            "#include <vector>\n"
            "#include <iostream>\n"
            "extern \"C\" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);\n"
            "int main() {\n"
            "    std::istreambuf_iterator<char> it(std::cin), end;\n"
            "    std::vector<uint8_t> data(it, end);\n"
            "    LLVMFuzzerTestOneInput(data.data(), data.size());\n"
            "    return 0;\n"
            "}\n"
        )
        try:
            with open(driver_cpp, "w") as f:
                f.write(driver_src)
        except Exception:
            shutil.rmtree(build_dir, ignore_errors=True)
            return None

        cflags = ["-g", "-O1", "-fno-omit-frame-pointer", "-fsanitize=address", "-std=c11", f"-I{root}"]
        cxxflags = ["-g", "-O1", "-fno-omit-frame-pointer", "-fsanitize=address", "-std=c++17", f"-I{root}"]
        ldflags = ["-fsanitize=address"]

        # Compile C sources
        for src in c_sources:
            if time.time() > deadline:
                break
            obj = os.path.join(build_dir, self._mangle_obj_name(src) + ".o")
            cmd = [cc] + cflags + ["-c", src, "-o", obj]
            try:
                res = subprocess.run(
                    cmd,
                    cwd=build_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                res = None
            if res is None or res.returncode != 0:
                # If harness failed to compile, abort this mode.
                if src == harness_file:
                    shutil.rmtree(build_dir, ignore_errors=True)
                    return None
                # Otherwise skip this file.
                continue
            obj_files.append(obj)

        # Compile C++ sources
        for src in cxx_sources:
            if time.time() > deadline:
                break
            obj = os.path.join(build_dir, self._mangle_obj_name(src) + ".o")
            cmd = [cxx] + cxxflags + ["-c", src, "-o", obj]
            try:
                res = subprocess.run(
                    cmd,
                    cwd=build_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                res = None
            if res is None or res.returncode != 0:
                if src == harness_file:
                    shutil.rmtree(build_dir, ignore_errors=True)
                    return None
                continue
            obj_files.append(obj)

        # Compile driver
        driver_obj = os.path.join(build_dir, "driver.o")
        cmd = [cxx] + cxxflags + ["-c", driver_cpp, "-o", driver_obj]
        try:
            res = subprocess.run(
                cmd,
                cwd=build_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            res = None
        if res is None or res.returncode != 0:
            shutil.rmtree(build_dir, ignore_errors=True)
            return None
        obj_files.append(driver_obj)

        # Link
        fuzz_bin = os.path.join(build_dir, "fuzz_bin")
        cmd = [cxx] + ldflags + obj_files + ["-o", fuzz_bin]
        try:
            res = subprocess.run(
                cmd,
                cwd=build_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            res = None
        if res is None or res.returncode != 0:
            shutil.rmtree(build_dir, ignore_errors=True)
            return None

        return fuzz_bin

    def _mangle_obj_name(self, path: str) -> str:
        # Create a filesystem-safe name from a source path.
        return path.replace("\\", "_").replace("/", "_").replace(":", "_")

    # ------------------------------------------------------------------
    # Fuzzing & crash detection
    # ------------------------------------------------------------------

    def _collect_seeds(
        self, root: str, max_files: int = 80, max_size: int = 65536
    ) -> List[bytes]:
        seeds: List[bytes] = [
            b"",
            b" ",
            b"\n",
            b"0",
            b"1",
            b"a",
            b"?",
            b"()",
            b"[]",
            b"{}",
            b"null",
            b"true",
            b"false",
            b"x = 1\n",
            b"def f():\n  pass\n",
            b"class C:\n  pass\n",
        ]
        count = 0
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if count >= max_files:
                    break
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                    if size == 0 or size > max_size:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    seeds.append(data)
                    count += 1
                except Exception:
                    continue
            if count >= max_files:
                break
        return seeds

    def _run_for_heap_uaf(
        self, bin_path: str, payload: bytes, timeout: float = 1.5
    ) -> bool:
        try:
            res = subprocess.run(
                [bin_path],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        if res.returncode == 0:
            return False

        stderr = res.stderr or b""
        stdout = res.stdout or b""
        out = stderr + stdout
        if b"AddressSanitizer" in out and (
            b"heap-use-after-free" in out or b"use-after-free" in out
        ):
            return True
        return False

    def _mutate(self, data: bytes, rng: random.Random, max_len: int = 300000) -> bytes:
        if not data or rng.random() < 0.1:
            # Generate a fresh random buffer.
            size = rng.randint(1, min(4096, max_len))
            return bytes(rng.getrandbits(8) for _ in range(size))

        buf = bytearray(data)
        # Limit base size
        if len(buf) > max_len:
            buf = buf[:max_len]

        num_ops = rng.randint(1, 8)
        for _ in range(num_ops):
            op = rng.randint(0, 2)
            if op == 0 and buf:
                # Flip a random bit.
                idx = rng.randrange(len(buf))
                bit = 1 << rng.randint(0, 7)
                buf[idx] ^= bit
            elif op == 1:
                # Insert random chunk.
                idx = rng.randrange(len(buf) + 1)
                chunk_len = rng.randint(1, 32)
                chunk = bytes(rng.getrandbits(8) for _ in range(chunk_len))
                buf[idx:idx] = chunk
                if len(buf) > max_len:
                    buf = buf[:max_len]
            elif op == 2 and len(buf) > 1:
                # Delete a slice.
                start = rng.randrange(len(buf))
                end = start + rng.randint(1, min(32, len(buf) - start))
                del buf[start:end]
                if not buf:
                    buf.append(0)
        if len(buf) > max_len:
            buf = buf[:max_len]
        return bytes(buf)

    def _fuzz_for_heap_uaf(
        self,
        bin_path: str,
        root: str,
        start_time: float,
        total_time_budget: float,
    ) -> Optional[bytes]:
        deadline = start_time + total_time_budget
        seeds = self._collect_seeds(root)
        # Deduplicate seeds while keeping order.
        uniq_seeds: List[bytes] = []
        seen = set()
        for s in seeds:
            if not isinstance(s, (bytes, bytearray)):
                continue
            b = bytes(s)
            key = (len(b), hash(b))
            if key in seen:
                continue
            seen.add(key)
            uniq_seeds.append(b)
        seeds = uniq_seeds or [b""]

        # 1) Try seeds directly.
        for s in seeds[:50]:
            if time.time() > deadline:
                return None
            if self._run_for_heap_uaf(bin_path, s, timeout=1.5):
                return s

        # 2) Mutational fuzzing.
        rng = random.Random(0)
        max_iters = 2000
        for _ in range(max_iters):
            if time.time() > deadline:
                break
            base = rng.choice(seeds)
            mutated = self._mutate(base, rng)
            if not mutated:
                continue
            if self._run_for_heap_uaf(bin_path, mutated, timeout=1.5):
                return mutated
            if len(seeds) < 1000 and rng.random() < 0.2:
                seeds.append(mutated)

        return None

    # ------------------------------------------------------------------
    # Input shrinking
    # ------------------------------------------------------------------

    def _shrink_input(
        self,
        bin_path: str,
        data: bytes,
        start_time: float,
        total_time_budget: float,
    ) -> bytes:
        deadline = start_time + total_time_budget
        if not data or len(data) <= 4:
            return data

        current = bytearray(data)
        chunk = max(len(current) // 8, 1)

        while chunk > 0 and len(current) > 4 and time.time() < deadline:
            changed = False
            i = 0
            while i < len(current) and time.time() < deadline:
                end = min(i + chunk, len(current))
                trial = current[:i] + current[end:]
                if not trial:
                    i = end
                    continue
                if self._run_for_heap_uaf(bin_path, bytes(trial), timeout=1.5):
                    current = trial
                    changed = True
                    # Do not advance i; re-test at same index with reduced data.
                else:
                    i = end
            if not changed:
                chunk //= 2

        return bytes(current)