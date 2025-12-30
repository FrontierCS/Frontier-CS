import os
import re
import math
import tarfile
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = b'{"a":1,"a":2}'
        try:
            root = self._prepare_source_tree(src_path)
            exe_paths = self._build_and_find_executables(root)
            if not exe_paths:
                return fallback

            candidates = self._gather_candidate_inputs(root, target_len=60)
            synthetic = self._synthetic_candidates()
            candidates.extend([c for c in synthetic if c not in candidates])

            best = None
            best_len = 10**9

            for exe in exe_paths[:20]:
                for data in candidates[:400]:
                    ok, mode = self._triggers_sanitizer_crash(exe, data)
                    if ok:
                        reduced = self._ddmin_reduce(exe, data, mode, max_checks=50)
                        if len(reduced) < best_len:
                            best = reduced
                            best_len = len(reduced)
                            if best_len <= 30:
                                return best
                if best is not None:
                    return best

            return best if best is not None else fallback
        except Exception:
            return fallback

    def _prepare_source_tree(self, src_path: str) -> str:
        p = Path(src_path)
        if p.is_dir():
            return str(p.resolve())

        tmp = tempfile.mkdtemp(prefix="arvo_src_")
        try:
            with tarfile.open(str(p), "r:*") as tf:
                tf.extractall(tmp)
        except Exception:
            return str(Path(src_path).resolve())

        entries = [Path(tmp) / e for e in os.listdir(tmp)]
        dirs = [e for e in entries if e.is_dir()]
        if len(dirs) == 1 and all((d == dirs[0] or not d.exists()) for d in dirs):
            return str(dirs[0].resolve())
        return str(Path(tmp).resolve())

    def _run_cmd(self, cmd: List[str], cwd: str, env: dict, timeout: int) -> Tuple[int, bytes, bytes]:
        try:
            p = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            return p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
            err = e.stderr or b""
            return 124, out, err
        except Exception as e:
            return 127, b"", (str(e).encode("utf-8", "ignore"))

    def _build_and_find_executables(self, root: str) -> List[str]:
        env = os.environ.copy()
        flags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined"
        env.setdefault("CC", "gcc")
        env.setdefault("CXX", "g++")
        env["CFLAGS"] = (env.get("CFLAGS", "") + " " + flags).strip()
        env["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " " + flags).strip()
        env["LDFLAGS"] = (env.get("LDFLAGS", "") + " " + flags).strip()

        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
        if env["ASAN_OPTIONS"]:
            env["ASAN_OPTIONS"] += ":"
        env["ASAN_OPTIONS"] += "detect_leaks=0:abort_on_error=1:halt_on_error=1"
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "")
        if env["UBSAN_OPTIONS"]:
            env["UBSAN_OPTIONS"] += ":"
        env["UBSAN_OPTIONS"] += "halt_on_error=1:abort_on_error=1:print_stacktrace=1"

        rootp = Path(root)

        build_dirs = []

        build_sh = rootp / "build.sh"
        if build_sh.is_file():
            self._run_cmd(["bash", str(build_sh)], cwd=root, env=env, timeout=120)
            build_dirs.append(root)

        cmake_lists = rootp / "CMakeLists.txt"
        if cmake_lists.is_file():
            bdir = rootp / "build_asan"
            bdir.mkdir(exist_ok=True)
            cmake_cmd = [
                "cmake",
                "-S",
                str(rootp),
                "-B",
                str(bdir),
                "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                f"-DCMAKE_C_FLAGS={env.get('CFLAGS','')}",
                f"-DCMAKE_CXX_FLAGS={env.get('CXXFLAGS','')}",
                f"-DCMAKE_EXE_LINKER_FLAGS={env.get('LDFLAGS','')}",
            ]
            self._run_cmd(cmake_cmd, cwd=root, env=env, timeout=120)
            self._run_cmd(["cmake", "--build", str(bdir), "-j", "8"], cwd=root, env=env, timeout=180)
            build_dirs.append(str(bdir))

        makefile = rootp / "Makefile"
        if makefile.is_file():
            self._run_cmd(["make", "clean"], cwd=root, env=env, timeout=60)
            self._run_cmd(["make", "-j", "8"], cwd=root, env=env, timeout=180)
            build_dirs.append(root)

        exes = []
        seen = set()
        for d in [root] + build_dirs:
            for exe in self._collect_executables(d):
                if exe not in seen:
                    seen.add(exe)
                    exes.append(exe)

        if not exes:
            exes = self._attempt_naive_compile(root, env)

        exes = self._filter_working_executables(exes, env)
        return exes

    def _collect_executables(self, base: str) -> List[str]:
        basep = Path(base)
        res = []
        for p in basep.rglob("*"):
            try:
                if not p.is_file():
                    continue
                if p.suffix in (".o", ".a", ".so", ".dylib", ".dll", ".py", ".sh", ".txt", ".md", ".cmake"):
                    continue
                st = p.stat()
                if st.st_size < 16:
                    continue
                if not os.access(str(p), os.X_OK):
                    continue
                with p.open("rb") as f:
                    head = f.read(4)
                if head != b"\x7fELF":
                    continue
                res.append(str(p))
            except Exception:
                continue
        res.sort(key=lambda x: (len(Path(x).parts), os.path.getsize(x)))
        return res

    def _attempt_naive_compile(self, root: str, env: dict) -> List[str]:
        rootp = Path(root)
        cpp_files = list(rootp.rglob("*.cpp")) + list(rootp.rglob("*.cc")) + list(rootp.rglob("*.cxx"))
        if not cpp_files:
            return []

        main_files = []
        for f in cpp_files:
            try:
                txt = f.read_text(errors="ignore")
            except Exception:
                continue
            if "int main" in txt:
                main_files.append(f)

        if not main_files:
            return []

        out = rootp / "a.out"
        srcs = [str(f) for f in cpp_files]
        cmd = [env.get("CXX", "g++")] + env.get("CXXFLAGS", "").split() + srcs + env.get("LDFLAGS", "").split() + ["-o", str(out)]
        self._run_cmd(cmd, cwd=root, env=env, timeout=180)
        if out.is_file() and os.access(str(out), os.X_OK):
            return [str(out)]
        return []

    def _filter_working_executables(self, exes: List[str], env: dict) -> List[str]:
        good = []
        for exe in exes:
            rc, _, _ = self._run_cmd([exe, "--help"], cwd=str(Path(exe).parent), env=env, timeout=1)
            if rc == 124:
                continue
            rc2, _, _ = self._run_with_input(exe, b"", mode="stdin", env=env, timeout=1)
            if rc2 == 124:
                continue
            good.append(exe)

        def score(exe_path: str) -> Tuple[int, int]:
            name = Path(exe_path).name.lower()
            pri = 10
            for k in ("fuzz", "poc", "repro", "driver", "test", "run"):
                if k in name:
                    pri = 0
                    break
            size = os.path.getsize(exe_path)
            return pri, size

        good.sort(key=score)
        return good

    def _run_with_input(self, exe: str, data: bytes, mode: str, env: dict, timeout: float) -> Tuple[int, bytes, bytes]:
        try:
            if mode == "stdin":
                p = subprocess.run(
                    [exe],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env=env,
                )
                return p.returncode, p.stdout, p.stderr

            with tempfile.NamedTemporaryFile(delete=False) as tf:
                tf.write(data)
                tf.flush()
                tmpname = tf.name
            try:
                p = subprocess.run(
                    [exe, tmpname],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env=env,
                )
                return p.returncode, p.stdout, p.stderr
            finally:
                try:
                    os.unlink(tmpname)
                except Exception:
                    pass
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
            err = e.stderr or b""
            return 124, out, err
        except Exception as e:
            return 127, b"", (str(e).encode("utf-8", "ignore"))

    def _is_sanitizer_crash(self, rc: int, err: bytes) -> bool:
        if rc == 0 or rc == 124:
            return False
        e = err.lower() if isinstance(err, (bytes, bytearray)) else str(err).encode().lower()
        needles = [
            b"addresssanitizer",
            b"undefinedbehaviorsanitizer",
            b"asan:",
            b"ubsan:",
            b"heap-use-after-free",
            b"use-after-free",
            b"double-free",
            b"attempting double-free",
            b"free(): double free",
            b"double free or corruption",
            b"sanitizer",
            b"error:",
        ]
        if any(n in e for n in needles):
            return True
        if rc < 0:
            return True
        return False

    def _triggers_sanitizer_crash(self, exe: str, data: bytes) -> Tuple[bool, str]:
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
        if env["ASAN_OPTIONS"]:
            env["ASAN_OPTIONS"] += ":"
        env["ASAN_OPTIONS"] += "detect_leaks=0:abort_on_error=1:halt_on_error=1"
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "")
        if env["UBSAN_OPTIONS"]:
            env["UBSAN_OPTIONS"] += ":"
        env["UBSAN_OPTIONS"] += "halt_on_error=1:abort_on_error=1:print_stacktrace=1"

        rc, _, err = self._run_with_input(exe, data, mode="stdin", env=env, timeout=1.0)
        if self._is_sanitizer_crash(rc, err):
            return True, "stdin"

        rc, _, err = self._run_with_input(exe, data, mode="file", env=env, timeout=1.0)
        if self._is_sanitizer_crash(rc, err):
            return True, "file"

        return False, ""

    def _ddmin_reduce(self, exe: str, data: bytes, mode: str, max_checks: int = 50) -> bytes:
        if len(data) <= 1:
            return data

        env = os.environ.copy()
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
        if env["ASAN_OPTIONS"]:
            env["ASAN_OPTIONS"] += ":"
        env["ASAN_OPTIONS"] += "detect_leaks=0:abort_on_error=1:halt_on_error=1"
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "")
        if env["UBSAN_OPTIONS"]:
            env["UBSAN_OPTIONS"] += ":"
        env["UBSAN_OPTIONS"] += "halt_on_error=1:abort_on_error=1:print_stacktrace=1"

        def check(inp: bytes) -> bool:
            rc, _, err = self._run_with_input(exe, inp, mode=mode, env=env, timeout=1.0)
            return self._is_sanitizer_crash(rc, err)

        if not check(data):
            return data

        n = 2
        cur = data
        checks = 0
        while len(cur) >= 2 and checks < max_checks:
            L = len(cur)
            chunk = int(math.ceil(L / n))
            reduced = False
            i = 0
            while i < L and checks < max_checks:
                start = i
                end = min(L, i + chunk)
                trial = cur[:start] + cur[end:]
                checks += 1
                if trial and check(trial):
                    cur = trial
                    L = len(cur)
                    n = max(2, n - 1)
                    reduced = True
                    break
                i += chunk

            if not reduced:
                if n >= L:
                    break
                n = min(L, n * 2)
        return cur

    def _gather_candidate_inputs(self, root: str, target_len: int = 60) -> List[bytes]:
        rootp = Path(root)
        files = []
        exclude_ext = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
            ".o", ".a", ".so", ".dylib", ".dll",
            ".py", ".sh", ".bat", ".ps1",
            ".md", ".rst", ".txt", ".cmake",
            ".json", ".yml", ".yaml", ".toml", ".ini",
            ".png", ".jpg", ".jpeg", ".gif", ".pdf",
        }
        for p in rootp.rglob("*"):
            try:
                if not p.is_file():
                    continue
                if p.name.startswith("."):
                    continue
                if p.suffix.lower() in exclude_ext and p.stat().st_size > 1024:
                    continue
                sz = p.stat().st_size
                if sz <= 0 or sz > 4096:
                    continue
                if p.suffix.lower() in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".o", ".a", ".so", ".dylib"}:
                    continue
                files.append(p)
            except Exception:
                continue

        files.sort(key=lambda x: (abs(x.stat().st_size - target_len), x.stat().st_size))
        out = []
        seen = set()
        for p in files[:300]:
            try:
                b = p.read_bytes()
                if not b or len(b) > 4096:
                    continue
                h = hash(b)
                if h in seen:
                    continue
                seen.add(h)
                out.append(b)
            except Exception:
                continue
        return out

    def _synthetic_candidates(self) -> List[bytes]:
        c = []

        # JSON duplicates
        c.append(b'{"a":1,"a":2}')
        c.append(b'{"a":{"b":1,"b":2}}')
        c.append(b'{"a":[1,2,3],"a":[4]}')
        c.append(b'{"a":1,"b":2,"b":3}')
        c.append(b'{"a":[{"b":1,"b":2}]}')
        c.append(b'{"a":{"b":{"c":1,"c":2}}}')
        c.append(b'{"x":0,"y":{"k":1,"k":2},"z":3}')
        c.append(b'{"a":"1","a":"2"}')

        # YAML duplicates
        c.append(b"a: 1\na: 2\n")
        c.append(b"root:\n  a: 1\n  a: 2\n")
        c.append(b"a: {b: 1, b: 2}\n")

        # INI/TOML duplicates
        c.append(b"a=1\na=2\n")
        c.append(b"[s]\na=1\na=2\n")
        c.append(b"a = 1\na = 2\n")

        # XML duplicate attribute / element name
        c.append(b'<a x="1" x="2"/>')
        c.append(b"<r><a/><a/></r>")

        # Custom-ish duplicates
        c.append(b"(a 1)(a 2)")
        c.append(b"node a\nnode a\n")

        # Add some mild padding variants without changing tokens too much
        for base in [b'{"a":1,"a":2}', b"a=1\na=2\n", b"a: 1\na: 2\n"]:
            c.append(base + b"\n")
            c.append(b" " + base + b"\n")

        # Dedup preserve order
        seen = set()
        out = []
        for x in c:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out