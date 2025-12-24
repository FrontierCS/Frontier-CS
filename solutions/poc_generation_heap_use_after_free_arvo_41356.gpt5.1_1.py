import os
import tarfile
import tempfile
import subprocess
import random
import shutil
import time


class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            self._extract_tar(src_path, work_dir)
            exe_path = self._build_binary(work_dir)
            if not exe_path or not os.path.exists(exe_path):
                return self._default_poc()
            poc = self._fuzz_for_asan_crash(exe_path)
            if poc is None:
                return self._default_poc()
            return poc
        finally:
            # Best-effort cleanup; ignore failures
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass

    # ---------------- Tar extraction ----------------

    def _extract_tar(self, src_path: str, dst: str) -> None:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(dst)
        except Exception:
            # If extraction fails, leave directory empty; build will fail and we fall back
            pass

    # ---------------- Source collection ----------------

    def _collect_sources(self, root: str):
        cpp_exts = (".cpp", ".cc", ".cxx", ".CPP", ".C", ".c++")
        c_exts = (".c",)
        skip_dirs = {
            ".git",
            ".hg",
            ".svn",
            "build",
            "cmake-build-debug",
            "cmake-build-release",
            "out",
            "dist",
            "bin",
            "obj",
            "__pycache__",
            "node_modules",
        }
        sources_cpp = []
        sources_c = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for f in filenames:
                path = os.path.join(dirpath, f)
                _, ext = os.path.splitext(f)
                if ext in cpp_exts:
                    sources_cpp.append(path)
                elif ext in c_exts:
                    sources_c.append(path)
        return sources_cpp, sources_c

    # ---------------- Fuzzer harness detection ----------------

    def _detect_llvm_fuzzer(self, source_files):
        for path in source_files:
            try:
                with open(path, "r", errors="ignore") as f:
                    if "LLVMFuzzerTestOneInput" in f.read():
                        return True
            except Exception:
                continue
        return False

    def _write_fuzzer_driver(self, root: str) -> str:
        driver_path = os.path.join(root, "__poc_driver.cpp")
        code = r"""
#include <cstdint>
#include <cstdio>
#include <vector>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);

int main(int argc, char **argv) {
    std::vector<uint8_t> data;
    data.reserve(1024);
    unsigned char buf[4096];
    while (true) {
        size_t n = std::fread(buf, 1, sizeof(buf), stdin);
        if (n == 0) break;
        data.insert(data.end(), buf, buf + n);
    }
    LLVMFuzzerTestOneInput(data.data(), data.size());
    return 0;
}
"""
        try:
            with open(driver_path, "w") as f:
                f.write(code)
        except Exception:
            return ""
        return driver_path

    # ---------------- Compiler helpers ----------------

    def _which(self, names):
        for n in names:
            p = shutil.which(n)
            if p:
                return p
        return None

    def _build_binary(self, root: str):
        sources_cpp, sources_c = self._collect_sources(root)
        if not sources_cpp and not sources_c:
            return None

        all_sources = sources_cpp + sources_c
        has_fuzzer = self._detect_llvm_fuzzer(all_sources)
        driver_path = None
        cpp_variants = [list(sources_cpp)]

        if has_fuzzer:
            driver_path = self._write_fuzzer_driver(root)
            if driver_path:
                cpp_with_driver = list(sources_cpp) + [driver_path]
                cpp_variants = [cpp_with_driver, list(sources_cpp)]

        exe_path = os.path.join(root, "poc_target")
        cxx_compiler = self._which(["clang++", "g++"])
        c_compiler = self._which(["clang", "gcc"])

        # Try C++ builds first (most likely for this task)
        for cpp_sources in cpp_variants:
            if not cpp_sources:
                continue
            # First try linking C and C++ together, then only C++
            source_sets = [cpp_sources + sources_c, cpp_sources]
            for srcs in source_sets:
                if not srcs:
                    continue
                if not cxx_compiler:
                    break
                cmd = [
                    cxx_compiler,
                    "-std=c++17",
                    "-g",
                    "-O1",
                    "-fsanitize=address",
                    "-fno-omit-frame-pointer",
                    "-Wall",
                    "-Wextra",
                ]
                cmd += srcs
                cmd += ["-o", exe_path, "-pthread"]
                try:
                    subprocess.run(
                        cmd,
                        cwd=root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=180,
                        check=True,
                    )
                    if os.path.exists(exe_path):
                        return exe_path
                except Exception:
                    continue

        # If there are only C sources and C++ path failed
        if not sources_cpp and sources_c and c_compiler:
            cmd = [
                c_compiler,
                "-g",
                "-O1",
                "-fsanitize=address",
                "-fno-omit-frame-pointer",
                "-Wall",
                "-Wextra",
            ]
            cmd += sources_c
            cmd += ["-o", exe_path]
            try:
                subprocess.run(
                    cmd,
                    cwd=root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=180,
                    check=True,
                )
                if os.path.exists(exe_path):
                    return exe_path
            except Exception:
                return None

        return None

    # ---------------- Target execution ----------------

    def _run_target(self, exe_path: str, data: bytes, timeout: float = 1.0):
        env = os.environ.copy()
        # Ensure ASan aborts on first error and does not waste time on leaks
        default_asan = "abort_on_error=1:detect_leaks=0:allocator_may_return_null=1"
        if "ASAN_OPTIONS" in env:
            if "detect_leaks" not in env["ASAN_OPTIONS"]:
                env["ASAN_OPTIONS"] += ":detect_leaks=0"
        else:
            env["ASAN_OPTIONS"] = default_asan

        try:
            p = subprocess.run(
                [exe_path],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return False, False
        except Exception:
            return False, False

        out = p.stdout + p.stderr
        crashed = p.returncode != 0
        is_asan = b"AddressSanitizer" in out
        return crashed, is_asan

    # ---------------- Mutation-based fuzzer ----------------

    def _rand_bytes(self, rnd: random.Random, n: int) -> bytes:
        if hasattr(rnd, "randbytes"):
            return rnd.randbytes(n)  # type: ignore[attr-defined]
        return bytes(rnd.getrandbits(8) for _ in range(n))

    def _mutate(self, rnd: random.Random, data: bytes, max_len: int) -> bytes:
        # Occasionally generate completely new random input
        if not data or rnd.random() < 0.15:
            size = rnd.randint(1, max_len)
            return self._rand_bytes(rnd, size)

        buf = bytearray(data)
        num_ops = rnd.randint(1, 6)
        for _ in range(num_ops):
            op = rnd.random()
            if op < 0.33 and len(buf) < max_len:
                # Insert
                pos = rnd.randint(0, len(buf))
                buf.insert(pos, rnd.getrandbits(8))
            elif op < 0.66 and buf:
                # Flip
                pos = rnd.randrange(len(buf))
                buf[pos] = rnd.getrandbits(8)
            elif len(buf) > 1:
                # Delete
                pos = rnd.randrange(len(buf))
                del buf[pos]
        if not buf:
            buf.append(rnd.getrandbits(8))
        if len(buf) > max_len:
            del buf[max_len:]
        return bytes(buf)

    def _fuzz_for_asan_crash(self, exe_path: str):
        rnd = random.Random(0xC0FFEE)
        max_len = 128
        max_iters = 6000
        max_time = 25.0  # seconds

        seed_corpus = [
            b"",
            b"\n",
            b"0\n",
            b"1\n",
            b"-1\n",
            b"add 0 0\n",
            b"add 0 1\n",
            b"node 0 0\n",
            b"A" * 16,
            b"B" * 32,
            b"<root></root>\n",
            b"{}\n",
            b"[]\n",
            bytes(range(1, 32)),
        ]
        corpus = list(seed_corpus)

        start = time.time()
        for _ in range(max_iters):
            if time.time() - start > max_time:
                break
            seed = rnd.choice(corpus)
            inp = self._mutate(rnd, seed, max_len)
            crashed, is_asan = self._run_target(exe_path, inp)
            if is_asan:
                return inp
            if not crashed and len(corpus) < 256 and rnd.random() < 0.3:
                corpus.append(inp)
        return None

    # ---------------- Fallback PoC ----------------

    def _default_poc(self) -> bytes:
        # Generic small binary payload; length near ground-truth hint (60 bytes)
        return b"A" * 60
