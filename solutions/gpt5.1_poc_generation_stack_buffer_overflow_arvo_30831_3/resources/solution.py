import os
import tarfile
import tempfile
import subprocess
import shutil
import random
import time
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            project_root = self._extract_project(src_path, work_dir)
            poc = self._generate_poc(project_root)
            if poc is None:
                # Fallback payload if everything fails
                return b"A" * 21
            return poc
        except Exception:
            # In case of unexpected error, still return something
            return b"A" * 21
        finally:
            # Best-effort cleanup
            shutil.rmtree(work_dir, ignore_errors=True)

    # ---------------- Extraction / Project root ----------------

    def _extract_project(self, tar_path: str, dst_dir: str) -> str:
        with tarfile.open(tar_path, "r:*") as tar:
            tar.extractall(dst_dir)
        # Determine project root: if single subdir, use that
        entries = [e for e in os.listdir(dst_dir) if not e.startswith(".")]
        if len(entries) == 1:
            root = os.path.join(dst_dir, entries[0])
            if os.path.isdir(root):
                return root
        return dst_dir

    # ---------------- High-level PoC generation ----------------

    def _generate_poc(self, project_root: str) -> bytes | None:
        # Strategy 1: Detect libFuzzer harness and build custom replayer
        exe = self._build_with_llvmfuzzer_replayer(project_root)
        if exe is not None:
            poc = self._fuzz_for_asan(
                exe_path=exe,
                target_func_substring="AppendUintOption",
                max_iterations=1200,
                max_len=64,
                timeout_per_run=0.2,
            )
            if poc is not None:
                minimized = self._minimize_payload(
                    exe_path=exe,
                    payload=poc,
                    target_func_substring="AppendUintOption",
                    timeout_per_run=0.2,
                    target_len=21,
                )
                return minimized

        # Strategy 2: Use build.sh if present, then fuzz produced binaries
        exe_list = self._build_with_script_and_find_bins(project_root, script_name="build.sh")
        for exe in exe_list:
            poc = self._fuzz_for_asan(
                exe_path=exe,
                target_func_substring="AppendUintOption",
                max_iterations=800,
                max_len=64,
                timeout_per_run=0.2,
            )
            if poc is not None:
                minimized = self._minimize_payload(
                    exe_path=exe,
                    payload=poc,
                    target_func_substring="AppendUintOption",
                    timeout_per_run=0.2,
                    target_len=21,
                )
                return minimized

        # Strategy 3: Use Makefile if present
        exe_list = self._build_with_make_and_find_bins(project_root)
        for exe in exe_list:
            poc = self._fuzz_for_asan(
                exe_path=exe,
                target_func_substring="AppendUintOption",
                max_iterations=800,
                max_len=64,
                timeout_per_run=0.2,
            )
            if poc is not None:
                minimized = self._minimize_payload(
                    exe_path=exe,
                    payload=poc,
                    target_func_substring="AppendUintOption",
                    timeout_per_run=0.2,
                    target_len=21,
                )
                return minimized

        # Strategy 4: Compile main-containing C files directly and fuzz
        exe_list = self._build_simple_mains(project_root)
        for exe in exe_list:
            poc = self._fuzz_for_asan(
                exe_path=exe,
                target_func_substring="AppendUintOption",
                max_iterations=800,
                max_len=64,
                timeout_per_run=0.2,
            )
            if poc is not None:
                minimized = self._minimize_payload(
                    exe_path=exe,
                    payload=poc,
                    target_func_substring="AppendUintOption",
                    timeout_per_run=0.2,
                    target_len=21,
                )
                return minimized

        # If everything failed, return None so caller can fallback
        return None

    # ---------------- Compiler selection ----------------

    def _choose_compiler(self, candidates: list[str]) -> str | None:
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path
        return None

    # ---------------- Strategy 1: libFuzzer replayer ----------------

    def _find_fuzzer_sources(self, root: str) -> list[str]:
        result = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".C")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", errors="ignore") as f:
                        data = f.read()
                except OSError:
                    continue
                if "LLVMFuzzerTestOneInput" in data:
                    result.append(path)
        return result

    def _build_with_llvmfuzzer_replayer(self, root: str) -> str | None:
        fuzzer_sources = self._find_fuzzer_sources(root)
        if not fuzzer_sources:
            return None

        cxx = self._choose_compiler(["clang++", "g++", "c++"])
        if cxx is None:
            return None

        replayer_path = os.path.join(root, "_poc_replayer.c")
        try:
            with open(replayer_path, "w") as f:
                f.write(
                    "#include <stdint.h>\n"
                    "#include <stdio.h>\n"
                    "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);\n"
                    "int main(void) {\n"
                    "    unsigned char buf[4096];\n"
                    "    size_t n = fread(buf, 1, sizeof(buf), stdin);\n"
                    "    LLVMFuzzerTestOneInput(buf, n);\n"
                    "    return 0;\n"
                    "}\n"
                )
        except OSError:
            return None

        # Collect all C/C++ sources except those containing main()
        srcs: list[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".C")):
                    continue
                full = os.path.join(dirpath, fn)
                # Skip our replayer; it will be added explicitly
                if os.path.abspath(full) == os.path.abspath(replayer_path):
                    continue
                try:
                    with open(full, "r", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "main(" in content:
                    continue
                # Use relative paths to avoid very long command line
                rel = os.path.relpath(full, root)
                srcs.append(rel)

        # Ensure fuzzer source files are included
        for fs in fuzzer_sources:
            rel = os.path.relpath(fs, root)
            if rel not in srcs:
                srcs.append(rel)

        # Add replayer
        srcs.append(os.path.relpath(replayer_path, root))

        if not srcs:
            return None

        exe_path = os.path.join(root, "_poc_fuzz_target")
        cmd = [
            cxx,
            "-fsanitize=address",
            "-g",
            "-O1",
            "-I.",
            "-o",
            exe_path,
        ] + srcs

        try:
            subprocess.run(
                cmd,
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except (subprocess.CalledProcessError, OSError):
            return None

        return exe_path if os.path.exists(exe_path) else None

    # ---------------- Strategy 2: build.sh ----------------

    def _build_with_script_and_find_bins(self, root: str, script_name: str) -> list[str]:
        script_path = os.path.join(root, script_name)
        if not os.path.isfile(script_path):
            return []

        # Try to run the build script with sanitizer flags
        env = os.environ.copy()
        env.setdefault("CC", "clang")
        env.setdefault("CXX", "clang++")
        extra_flags = "-fsanitize=address -g -O1"
        env["CFLAGS"] = env.get("CFLAGS", "") + " " + extra_flags
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " " + extra_flags
        env["LDFLAGS"] = env.get("LDFLAGS", "") + " -fsanitize=address"

        try:
            subprocess.run(
                ["bash", script_path],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            # Even if build fails, maybe some binaries were produced
            pass

        return self._find_elf_binaries(root)

    # ---------------- Strategy 3: Makefile ----------------

    def _build_with_make_and_find_bins(self, root: str) -> list[str]:
        makefile_dir = None
        # Prefer top-level Makefile
        if os.path.isfile(os.path.join(root, "Makefile")):
            makefile_dir = root
        else:
            # Search one level deep
            for dirpath, _, filenames in os.walk(root):
                if "Makefile" in filenames:
                    makefile_dir = dirpath
                    break

        if not makefile_dir:
            return []

        env = os.environ.copy()
        env.setdefault("CC", "clang")
        env.setdefault("CXX", "clang++")
        extra_flags = "-fsanitize=address -g -O1"
        env["CFLAGS"] = env.get("CFLAGS", "") + " " + extra_flags
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " " + extra_flags
        env["LDFLAGS"] = env.get("LDFLAGS", "") + " -fsanitize=address"

        try:
            subprocess.run(
                ["make", "-j8"],
                cwd=makefile_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

        return self._find_elf_binaries(root)

    # ---------------- Strategy 4: direct mains ----------------

    def _build_simple_mains(self, root: str) -> list[str]:
        # Find .c files that contain main() and try to build them individually
        c_comp = self._choose_compiler(["clang", "gcc", "cc"])
        if c_comp is None:
            return []
        exe_paths: list[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(".c"):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    with open(full, "r", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "main(" not in content:
                    continue
                rel = os.path.relpath(full, dirpath)
                exe = os.path.join(dirpath, os.path.splitext(fn)[0] + "_asan")
                cmd = [
                    c_comp,
                    "-fsanitize=address",
                    "-g",
                    "-O1",
                    "-I.",
                    rel,
                    "-o",
                    exe,
                ]
                try:
                    subprocess.run(
                        cmd,
                        cwd=dirpath,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    if os.path.exists(exe):
                        exe_paths.append(exe)
                except (subprocess.CalledProcessError, OSError):
                    continue
        return exe_paths

    # ---------------- ELF detection ----------------

    def _find_elf_binaries(self, root: str) -> list[str]:
        bins: list[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if not os.access(full, os.X_OK):
                    continue
                try:
                    with open(full, "rb") as f:
                        magic = f.read(4)
                except OSError:
                    continue
                if magic == b"\x7fELF":
                    bins.append(full)
        return bins

    # ---------------- Fuzzing ----------------

    def _initial_seeds(self) -> list[bytes]:
        seeds: list[bytes] = []

        # Very small and trivial seeds
        seeds.append(b"")
        seeds.append(b"\x00" * 4)
        seeds.append(b"\xff" * 4)
        seeds.append(bytes(range(1, 17)))

        # CoAP-like headers (Ver=1, Type=0(CON), TKL=0, Code=GET)
        seeds.append(b"\x40\x01\x00\x00")
        seeds.append(b"\x40\x01\x12\x34")
        seeds.append(b"\x44\x01\x00\x01")  # TKL=4
        # With extra data to reach around 21 bytes
        seeds.append(b"\x40\x01\x00\x00" + b"\xff" * 17)
        seeds.append(b"\x40\x01\x00\x00" + b"\x00" * 17)

        # Generic pattern around ground-truth size
        seeds.append(b"A" * 21)
        seeds.append(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" * 3)

        return seeds

    def _mutate(self, data: bytes, max_len: int) -> bytes:
        if not data:
            # If empty, generate random non-empty
            l = random.randint(1, max_len)
            return os.urandom(l)
        ba = bytearray(data)
        # Apply 1-4 random mutations
        for _ in range(random.randint(1, 4)):
            op = random.randint(0, 2)
            if op == 0 and len(ba) > 0:
                # Flip a random bit
                idx = random.randrange(len(ba))
                bit = 1 << random.randrange(8)
                ba[idx] ^= bit
            elif op == 1 and len(ba) < max_len:
                # Insert random byte
                idx = random.randrange(len(ba) + 1)
                ba[idx:idx] = bytes([random.randrange(256)])
            elif op == 2 and len(ba) > 1:
                # Delete random byte
                idx = random.randrange(len(ba))
                del ba[idx]
        if len(ba) > max_len:
            del ba[max_len:]
        return bytes(ba)

    def _run_and_check_asan(
        self,
        exe_path: str,
        payload: bytes,
        target_func_substring: str,
        timeout_per_run: float,
    ) -> bool:
        env = os.environ.copy()
        # Ensure ASAN aborts on error and does not care about leaks
        asan_opts = env.get("ASAN_OPTIONS", "")
        extra = "abort_on_error=1:detect_leaks=0"
        if asan_opts:
            asan_opts = asan_opts + ":" + extra
        else:
            asan_opts = extra
        env["ASAN_OPTIONS"] = asan_opts
        try:
            proc = subprocess.run(
                [exe_path],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_per_run,
                env=env,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False

        if not proc.stderr:
            return False
        try:
            stderr_text = proc.stderr.decode("utf-8", errors="ignore")
        except Exception:
            stderr_text = proc.stderr.decode("latin1", errors="ignore")

        if "ERROR: AddressSanitizer" in stderr_text and target_func_substring in stderr_text:
            return True
        return False

    def _fuzz_for_asan(
        self,
        exe_path: str,
        target_func_substring: str,
        max_iterations: int,
        max_len: int,
        timeout_per_run: float,
    ) -> bytes | None:
        random.seed(int(time.time() * 1000) & 0xFFFFFFFF)

        seeds = self._initial_seeds()

        # Try initial seeds first
        for s in seeds:
            payload = s[:max_len]
            if self._run_and_check_asan(exe_path, payload, target_func_substring, timeout_per_run):
                return payload

        # Random/mutation-based fuzzing
        if not seeds:
            seeds.append(os.urandom(8))

        for _ in range(max_iterations):
            base = random.choice(seeds)
            if random.random() < 0.7:
                payload = self._mutate(base, max_len)
            else:
                l = random.randint(1, max_len)
                payload = os.urandom(l)
            if self._run_and_check_asan(exe_path, payload, target_func_substring, timeout_per_run):
                return payload

        return None

    # ---------------- Minimization ----------------

    def _minimize_payload(
        self,
        exe_path: str,
        payload: bytes,
        target_func_substring: str,
        timeout_per_run: float,
        target_len: int | None = None,
    ) -> bytes:
        best = payload
        changed = True

        # Simple delta debugging: try removing one byte at a time
        while changed:
            changed = False
            if target_len is not None and len(best) <= target_len:
                break
            if len(best) <= 1:
                break
            for i in range(len(best)):
                trial = best[:i] + best[i + 1 :]
                if not trial:
                    continue
                if self._run_and_check_asan(exe_path, trial, target_func_substring, timeout_per_run):
                    best = trial
                    changed = True
                    break

        return best
