import os
import tarfile
import tempfile
import subprocess
import time
import random
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        random.seed(0)
        tmp_root = None
        try:
            tmp_root = self._extract_tarball(src_path)
            project_root = self._find_project_root(tmp_root)
            bin_path, is_asan = self._build_or_compile(project_root)
            if not bin_path or not os.path.isfile(bin_path):
                return self._default_poc()

            poc = self._fuzz_for_bug(bin_path, is_asan, time_budget=40.0)
            if poc is None:
                return self._default_poc()

            if is_asan:
                poc = self._shrink_asan_poc(bin_path, poc, time_budget=10.0, max_attempts=60)

            return poc
        except Exception:
            return self._default_poc()
        finally:
            if tmp_root and os.path.isdir(tmp_root):
                try:
                    shutil.rmtree(tmp_root, ignore_errors=True)
                except Exception:
                    pass

    # ------------------------------------------------------------------ #
    # Extraction and project discovery
    # ------------------------------------------------------------------ #
    def _extract_tarball(self, src_path: str) -> str:
        tmp_dir = tempfile.mkdtemp(prefix="poc_uaf_")
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(tmp_dir)
        return tmp_dir

    def _find_project_root(self, base: str) -> str:
        # BFS up to limited depth to find directory with a build script
        queue = [(base, 0)]
        visited = set()
        best = base
        max_depth = 3
        build_files = {"build.sh", "CMakeLists.txt", "Makefile", "makefile"}
        while queue:
            path, depth = queue.pop(0)
            if path in visited or depth > max_depth:
                continue
            visited.add(path)
            try:
                names = set(os.listdir(path))
            except Exception:
                continue
            if build_files & names:
                return path
            for name in names:
                if name.startswith("."):
                    continue
                child = os.path.join(path, name)
                if os.path.isdir(child):
                    queue.append((child, depth + 1))
        return best

    # ------------------------------------------------------------------ #
    # Building / compiling
    # ------------------------------------------------------------------ #
    def _build_or_compile(self, root: str):
        env = os.environ.copy()
        asan_flags = "-fsanitize=address -g -O0 -fno-omit-frame-pointer"
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            prev = env.get(key, "")
            env[key] = (prev + " " + asan_flags).strip()

        bin_path = None
        # 1) build.sh
        script = os.path.join(root, "build.sh")
        if os.path.isfile(script) and os.access(script, os.X_OK):
            self._run_cmd(["bash", script], cwd=root, env=env, timeout=120)
            bin_path = self._find_binary(root)

        # 2) CMake
        if not bin_path and os.path.isfile(os.path.join(root, "CMakeLists.txt")):
            build_dir = os.path.join(root, "build")
            os.makedirs(build_dir, exist_ok=True)
            self._run_cmd(["cmake", ".."], cwd=build_dir, env=env, timeout=120)
            self._run_cmd(["make", "-j4"], cwd=build_dir, env=env, timeout=240)
            bin_path = self._find_binary(build_dir) or self._find_binary(root)

        # 3) Makefile
        if not bin_path and (
            os.path.isfile(os.path.join(root, "Makefile"))
            or os.path.isfile(os.path.join(root, "makefile"))
        ):
            self._run_cmd(["make", "-j4"], cwd=root, env=env, timeout=240)
            bin_path = self._find_binary(root)

        is_asan = False
        if bin_path:
            is_asan = self._binary_has_asan(bin_path)

        # 4) Naive compile with explicit -fsanitize if we have no binary or no ASan
        if (not bin_path) or (not is_asan):
            naive_out = os.path.join(root, "naive_build_bin")
            if self._naive_compile(root, naive_out):
                bin_path = naive_out
                is_asan = self._binary_has_asan(bin_path)

        return bin_path, is_asan

    def _run_cmd(self, cmd, cwd=None, env=None, timeout=120):
        try:
            subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
        except Exception:
            pass

    def _find_binary(self, search_root: str):
        candidates = []
        root_depth = search_root.rstrip(os.sep).count(os.sep)
        for r, _, files in os.walk(search_root):
            for f in files:
                path = os.path.join(r, f)
                if not os.path.isfile(path):
                    continue
                if any(path.endswith(ext) for ext in (".so", ".a", ".o", ".lo", ".dll")):
                    continue
                if not os.access(path, os.X_OK):
                    continue
                try:
                    with open(path, "rb") as bf:
                        magic = bf.read(4)
                    if magic != b"\x7fELF":
                        continue
                except Exception:
                    continue
                name = os.path.basename(path).lower()
                score = 0.0
                if "." not in name:
                    score += 1.0
                for token in ("main", "app", "vuln", "target", "prog", "server", "client"):
                    if token in name:
                        score += 1.5
                if "test" in name or "example" in name or "sample" in name:
                    score -= 1.0
                depth = r.rstrip(os.sep).count(os.sep) - root_depth
                score -= 0.1 * max(depth, 0)
                candidates.append((score, path))
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]

    def _binary_has_asan(self, bin_path: str) -> bool:
        try:
            with open(bin_path, "rb") as f:
                data = f.read()
            return b"AddressSanitizer" in data
        except Exception:
            return False

    def _naive_compile(self, root: str, out_path: str) -> bool:
        sources = []
        for r, _, files in os.walk(root):
            for f in files:
                if f.endswith((".c", ".cc", ".cpp", ".cxx")):
                    sources.append(os.path.join(r, f))
        if not sources:
            return False
        compiler = "g++"
        cmd = [
            compiler,
            "-std=c++17",
            "-g",
            "-O0",
            "-fsanitize=address",
            "-fno-omit-frame-pointer",
        ] + sources + ["-o", out_path]
        try:
            subprocess.run(
                cmd,
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=240,
                check=False,
            )
        except Exception:
            return False
        return os.path.isfile(out_path)

    # ------------------------------------------------------------------ #
    # Fuzzing
    # ------------------------------------------------------------------ #
    def _initial_seeds(self):
        seeds = [
            b"",
            b"\n",
            b"A" * 16 + b"\n",
            b"0\n",
            b"1\n",
            b"-1\n",
            b"node\n",
            b"add\n",
            b"node 0\n",
            b"add 0 0\n",
            b"ADD 0 0\n",
            b"NODE 0 0\n",
            b"root\n",
            b"child\n",
            b"tree\n",
            b"BEGIN\nEND\n",
            b"{}\n",
            b"[]\n",
            b"()\n",
            b"<a></a>\n",
            b"func a(){}\n",
            b"add child child\n",
            b"node a\nnode a\n",
            b"add a b\nadd a b\n",
        ]
        # Pad some seeds to around 60 bytes
        seeds.append(b"A" * 60)
        seeds.append(b"node a\nadd a a\nadd a a\n" + b"B" * 20)
        return seeds

    def _run_target(self, bin_path: str, data: bytes, timeout: float = 0.5):
        try:
            proc = subprocess.run(
                [bin_path],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, b"", b"timeout"
        except Exception as e:
            return -1, b"", str(e).encode("utf-8", errors="ignore")

    def _is_asan_heap_uaf(self, stderr_bytes: bytes) -> bool:
        if b"ERROR: AddressSanitizer" not in stderr_bytes:
            return False
        lower = stderr_bytes.lower()
        if b"heap-use-after-free" in lower:
            return True
        if b"double-free" in lower:
            return True
        return False

    def _fuzz_for_bug(self, bin_path: str, is_asan: bool, time_budget: float = 40.0):
        start = time.time()
        rnd = random.Random(1)
        seeds = list(self._initial_seeds())
        corpus = list(seeds)
        crash_input = None

        while time.time() - start < time_budget:
            if seeds:
                data = seeds.pop(0)
            else:
                base = rnd.choice(corpus) if corpus else b""
                data = self._mutate(base, rnd, max_len=128)

            ret, out, err = self._run_target(bin_path, data, timeout=0.5)

            if is_asan:
                if self._is_asan_heap_uaf(err):
                    return data
            else:
                if ret != 0 or ret < 0:
                    if crash_input is None:
                        crash_input = data

            if ret == 0:
                if len(data) <= 256:
                    corpus.append(data)

        return crash_input

    def _mutate(self, data: bytes, rnd: random.Random, max_len: int = 128) -> bytes:
        if not data:
            length = rnd.randint(1, max_len)
            return bytes(rnd.getrandbits(8) for _ in range(length))

        buf = bytearray(data)
        num_ops = rnd.randint(1, max(1, len(buf) // 4))
        for _ in range(num_ops):
            op = rnd.randint(0, 2)
            if op == 0 and buf:
                idx = rnd.randrange(len(buf))
                buf[idx] = rnd.getrandbits(8)
            elif op == 1 and len(buf) < max_len:
                idx = rnd.randrange(len(buf) + 1)
                buf.insert(idx, rnd.getrandbits(8))
            elif op == 2 and buf:
                idx = rnd.randrange(len(buf))
                del buf[idx]
        if len(buf) > max_len:
            del buf[max_len:]
        return bytes(buf)

    # ------------------------------------------------------------------ #
    # Shrinking
    # ------------------------------------------------------------------ #
    def _shrink_asan_poc(self, bin_path: str, data: bytes, time_budget: float, max_attempts: int) -> bytes:
        start = time.time()
        rnd = random.Random(2)
        current = data
        attempts = 0
        while attempts < max_attempts and time.time() - start < time_budget and len(current) > 1:
            attempts += 1
            if len(current) == 0:
                break
            start_idx = rnd.randint(0, len(current) - 1)
            end_idx = rnd.randint(start_idx + 1, len(current))
            candidate = current[:start_idx] + current[end_idx:]
            ret, _, err = self._run_target(bin_path, candidate, timeout=0.5)
            if self._is_asan_heap_uaf(err):
                current = candidate
        return current

    # ------------------------------------------------------------------ #
    # Defaults
    # ------------------------------------------------------------------ #
    def _default_poc(self) -> bytes:
        # 60-byte default payload
        return b"A" * 60