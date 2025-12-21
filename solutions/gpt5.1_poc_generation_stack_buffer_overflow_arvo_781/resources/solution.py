import os
import tarfile
import tempfile
import shutil
import subprocess
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        workdir = tempfile.mkdtemp(prefix="arvo781_")
        try:
            self._extract_tarball(src_path, workdir)
            src_root = self._detect_root(workdir)
            binary = self._build_and_find_binary(src_root)
            if binary is not None:
                poc = self._find_poc_via_fuzz(binary)
                if poc is not None:
                    return poc
            return self._fallback_poc()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _extract_tarball(self, src_path: str, workdir: str) -> None:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(path=workdir)
        except Exception:
            # If extraction fails, leave directory empty; fallback PoC will be used.
            pass

    def _detect_root(self, workdir: str) -> str:
        try:
            entries = [os.path.join(workdir, e) for e in os.listdir(workdir)]
            dirs = [e for e in entries if os.path.isdir(e)]
            files = [e for e in entries if os.path.isfile(e)]
            if len(dirs) == 1 and not files:
                return dirs[0]
        except Exception:
            pass
        return workdir

    def _build_and_find_binary(self, src_root: str):
        env = os.environ.copy()
        san_flags = "-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1"
        cc = shutil.which("clang") or shutil.which("gcc") or "gcc"
        cxx = shutil.which("clang++") or shutil.which("g++") or "g++"
        env["CC"] = cc
        env["CXX"] = cxx

        def append_flag(name: str):
            prev = env.get(name, "")
            if san_flags not in prev:
                if prev:
                    env[name] = prev + " " + san_flags
                else:
                    env[name] = san_flags

        append_flag("CFLAGS")
        append_flag("CXXFLAGS")
        append_flag("LDFLAGS")

        # 1. Run build.sh if present
        build_sh = self._find_script(src_root, "build.sh")
        if build_sh:
            self._run_cmd(["bash", build_sh], cwd=os.path.dirname(build_sh), env=env, timeout=300)
            bins = self._find_candidate_binaries(src_root)
            if bins:
                return bins[0]

        # 2. CMake
        if os.path.exists(os.path.join(src_root, "CMakeLists.txt")):
            build_dir = os.path.join(src_root, "build")
            os.makedirs(build_dir, exist_ok=True)
            if self._run_cmd(["cmake", ".."], cwd=build_dir, env=env, timeout=300):
                self._run_cmd(["cmake", "--build", ".", "-j", "8"], cwd=build_dir, env=env, timeout=600)
                bins = self._find_candidate_binaries(build_dir)
                if not bins:
                    bins = self._find_candidate_binaries(src_root)
                if bins:
                    return bins[0]

        # 3. Autoconf configure + make
        configure = os.path.join(src_root, "configure")
        if os.path.exists(configure) and os.path.isfile(configure):
            try:
                os.chmod(configure, 0o755)
            except Exception:
                pass
            self._run_cmd(["./configure"], cwd=src_root, env=env, timeout=300)
            self._run_cmd(["make", "-j", "8"], cwd=src_root, env=env, timeout=600)
            bins = self._find_candidate_binaries(src_root)
            if bins:
                return bins[0]

        # 4. Make only
        makefile = os.path.join(src_root, "Makefile")
        if os.path.exists(makefile):
            self._run_cmd(["make", "-j", "8"], cwd=src_root, env=env, timeout=600)
            bins = self._find_candidate_binaries(src_root)
            if bins:
                return bins[0]

        # 5. As a last resort, search any executable already present
        bins = self._find_candidate_binaries(src_root)
        if bins:
            return bins[0]

        return None

    def _find_script(self, root: str, name: str):
        best = None
        best_depth = None
        for dirpath, _, filenames in os.walk(root):
            if name in filenames:
                path = os.path.join(dirpath, name)
                depth = path.count(os.sep)
                if best is None or depth < best_depth:
                    best = path
                    best_depth = depth
        return best

    def _run_cmd(self, cmd, cwd=None, env=None, timeout=300) -> bool:
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _find_candidate_binaries(self, base: str):
        bins = []
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                if not os.path.isfile(path):
                    continue
                lower = fn.lower()
                if lower.endswith((".a", ".so", ".dylib", ".dll", ".o", ".lo", ".la", ".obj")):
                    continue
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if not (st.st_mode & 0o111):
                    continue
                try:
                    with open(path, "rb") as f:
                        head = f.read(4)
                    if head != b"\x7fELF":
                        continue
                except Exception:
                    continue
                bins.append(path)

        def score(p: str):
            name = os.path.basename(p).lower()
            s = 0
            keywords = ["fuzz", "test", "pcre", "regex", "runner", "poc", "demo", "main"]
            for i, k in enumerate(keywords):
                if k in name:
                    s -= 10 * (len(keywords) - i)
            depth = p.count(os.sep)
            s += depth
            try:
                size_mb = os.path.getsize(p) // (1024 * 1024)
                s += size_mb
            except Exception:
                pass
            return s

        bins.sort(key=score)
        return bins

    def _find_poc_via_fuzz(self, binary: str):
        patterns = [
            "()", "(a)", "(b)", "(.)",
            "(a)(b)", "(a)(b)(c)", "((a))", "((a)(b))",
            "(a*)", "(a+)", "(a?)",
            "((a)*)", "((a)+)", "(a|b)", "((a|b))",
            "(ab)", "(ab)(cd)", "((ab))",
            "(a)(?:b)", "(?:a)(b)", "((?:a)(b))",
            "((a)(b)(c))", "(a(b(c)))",
            "()()",
            "()()()",
            "()()()()",
            "(a)(a)(a)(a)",
        ]
        subjects = [b"", b"a", b"b", b"ab", b"aaa", b"abcd", b"1234"]

        candidates = []
        for p in patterns:
            pb = p.encode("ascii", errors="ignore")
            candidates.append(pb)
            candidates.append(pb + b"\n")
            for s in subjects:
                candidates.append(pb + b"\n" + s)
                candidates.append(pb + b"\n" + s + b"\n")
                candidates.append(s + b"\n" + pb)
                candidates.append(s + b"\n" + pb + b"\n")

        # Deduplicate while preserving order
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        # Try deterministic candidates
        for data in unique_candidates:
            if self._triggers_bug(binary, data):
                return data

        # Random fuzzing as a backup
        rng = random.Random(781)
        charset = b"().*+?|[]{}^$\\ab01"
        max_iters = 300
        for _ in range(max_iters):
            length = rng.randint(1, 16)
            p = bytes(rng.choice(charset) for _ in range(length))
            # Ensure we have some parentheses
            if b"(" not in p:
                p = b"(" + p + b")"
            s = bytes(rng.choice(b"ab01") for _ in range(rng.randint(0, 8)))
            choice = rng.randint(0, 4)
            if choice == 0:
                data = p
            elif choice == 1:
                data = p + b"\n" + s
            elif choice == 2:
                data = s + b"\n" + p
            elif choice == 3:
                data = p + b"\n"
            else:
                data = p + b"\n" + s + b"\n"

            if self._triggers_bug(binary, data):
                return data

        return None

    def _triggers_bug(self, binary: str, data: bytes) -> bool:
        try:
            proc = subprocess.run(
                [binary],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        rc = proc.returncode
        out = proc.stdout + proc.stderr
        if b"ERROR: AddressSanitizer" in out or b"SUMMARY: AddressSanitizer" in out:
            return True
        if b"runtime error:" in out and b"UndefinedBehaviorSanitizer" in out:
            return True
        if rc < 0:
            # killed by signal (e.g., SIGSEGV)
            return True
        return False

    def _fallback_poc(self) -> bytes:
        # Generic short regex with multiple capturing groups
        return b"()()()()"
