import os
import re
import io
import sys
import tarfile
import time
import stat
import json
import math
import shlex
import shutil
import random
import tempfile
import subprocess
from typing import List, Tuple, Optional, Dict, Iterable


class Solution:
    def solve(self, src_path: str) -> bytes:
        start = time.monotonic()
        deadline = start + 170.0

        rnd = random.Random(0xC0FFEE)

        with tempfile.TemporaryDirectory(prefix="arvo_41356_") as td:
            root = os.path.join(td, "src")
            os.makedirs(root, exist_ok=True)
            self._extract_tarball_safe(src_path, root)
            proj_root = self._find_project_root(root)

            embedded = self._find_embedded_pocs(proj_root)
            magic_strings = self._extract_magic_strings(proj_root)

            prebuilt_exes = self._find_elf_executables(proj_root)
            build_dirs = []
            if not prebuilt_exes and time.monotonic() < deadline - 20:
                build_dirs = self._build_project(proj_root, deadline)

            exe_candidates = []
            for d in [proj_root] + build_dirs:
                exe_candidates.extend(self._find_elf_executables(d))
            exe_candidates = self._dedup_paths(exe_candidates)

            if not exe_candidates:
                raise RuntimeError("No executable found/built")

            exe_candidates = self._rank_executables(exe_candidates)

            # Try embedded PoCs first (validate by running)
            for exe in exe_candidates:
                mode = self._probe_invocation_mode(exe, deadline)
                if mode is None:
                    continue
                for b in embedded:
                    if self._is_crash(exe, mode, b, deadline):
                        bmin = self._minimize(exe, mode, b, deadline)
                        return bmin

            # Try repository sample/corpus inputs
            sample_inputs = self._collect_sample_inputs(proj_root)
            for exe in exe_candidates:
                mode = self._probe_invocation_mode(exe, deadline)
                if mode is None:
                    continue
                for b in sample_inputs:
                    if self._is_crash(exe, mode, b, deadline):
                        bmin = self._minimize(exe, mode, b, deadline)
                        return bmin

            # Fuzz
            for exe in exe_candidates:
                if time.monotonic() > deadline - 5:
                    break
                mode = self._probe_invocation_mode(exe, deadline)
                if mode is None:
                    continue
                crash = self._fuzz_find_crash(exe, mode, sample_inputs, embedded, magic_strings, rnd, deadline)
                if crash is not None:
                    bmin = self._minimize(exe, mode, crash, deadline)
                    return bmin

        raise RuntimeError("Failed to generate PoC")

    # ------------------------ Extraction ------------------------

    def _extract_tarball_safe(self, tar_path: str, out_dir: str) -> None:
        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        with tarfile.open(tar_path, "r:*") as tar:
            members = tar.getmembers()
            for m in members:
                if m.name.startswith("/") or ".." in m.name.split("/"):
                    continue
                dest = os.path.join(out_dir, m.name)
                if not is_within_directory(out_dir, dest):
                    continue
                tar.extract(m, out_dir)

    def _find_project_root(self, extracted_root: str) -> str:
        entries = [os.path.join(extracted_root, e) for e in os.listdir(extracted_root)]
        dirs = [p for p in entries if os.path.isdir(p)]
        if len(dirs) == 1 and not any(os.path.isfile(p) for p in entries):
            return dirs[0]
        return extracted_root

    # ------------------------ Discovery ------------------------

    def _walk_files(self, root: str, exts: Optional[Tuple[str, ...]] = None) -> Iterable[str]:
        skip_dirs = {
            ".git", ".svn", ".hg", "__pycache__", "node_modules", "build", "dist",
            "cmake-build-debug", "cmake-build-release", ".idea", ".vscode",
        }
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in skip_dirs and not d.startswith(".")]
            for f in fn:
                if f.startswith("."):
                    continue
                p = os.path.join(dp, f)
                if exts is None:
                    yield p
                else:
                    lf = f.lower()
                    if any(lf.endswith(e) for e in exts):
                        yield p

    def _read_file_limited(self, path: str, limit: int = 2_000_000) -> bytes:
        try:
            with open(path, "rb") as f:
                return f.read(limit)
        except Exception:
            return b""

    def _find_embedded_pocs(self, root: str) -> List[bytes]:
        # Try to extract hex arrays or escaped strings from sources
        src_exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".ipp")
        out: List[bytes] = []
        hex_re = re.compile(rb"0x([0-9a-fA-F]{2})")
        cstr_re = re.compile(rb'"((?:\\.|[^"\\]){1,4096})"')
        raw_re = re.compile(rb'R"\((.{1,4096}?)\)"', re.DOTALL)

        for p in self._walk_files(root, src_exts):
            data = self._read_file_limited(p, 1_000_000)
            if not data:
                continue

            # Hex byte arrays
            for m in re.finditer(rb"\{[^{}]{0,20000}?\}", data, re.DOTALL):
                block = m.group(0)
                hx = hex_re.findall(block)
                if 10 <= len(hx) <= 4096:
                    try:
                        b = bytes(int(x, 16) for x in hx)
                        if b and len(b) <= 4096:
                            out.append(b)
                    except Exception:
                        pass

            # Raw strings that look like sample inputs (JSON/XML/etc)
            for m in raw_re.finditer(data):
                b = m.group(1)
                b = b.replace(b"\r\n", b"\n")
                if 4 <= len(b) <= 4096:
                    out.append(b)

            # Normal strings (try unescaping)
            for m in cstr_re.finditer(data):
                s = m.group(1)
                if len(s) < 4 or len(s) > 2048:
                    continue
                if b"\\x" in s or b"\\n" in s or b"\\t" in s or b"\\\"" in s or b"\\0" in s:
                    try:
                        decoded = self._c_unescape_bytes(s)
                        if 4 <= len(decoded) <= 4096:
                            out.append(decoded)
                    except Exception:
                        pass

        # Also look for standalone PoC files by name
        name_keywords = ("poc", "crash", "repro", "testcase", "corpus", "seed")
        for p in self._walk_files(root, None):
            base = os.path.basename(p).lower()
            if any(k in base for k in name_keywords):
                b = self._read_file_limited(p, 1_000_000)
                if 1 <= len(b) <= 4096:
                    out.append(b)

        # Dedup while preserving order
        uniq = []
        seen = set()
        for b in out:
            h = (len(b), b[:64], b[-64:])
            if h in seen:
                continue
            seen.add(h)
            uniq.append(b)
        return uniq

    def _c_unescape_bytes(self, s: bytes) -> bytes:
        out = bytearray()
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c != 0x5C:  # backslash
                out.append(c)
                i += 1
                continue
            i += 1
            if i >= n:
                break
            esc = s[i]
            i += 1
            if esc == ord('n'):
                out.append(0x0A)
            elif esc == ord('r'):
                out.append(0x0D)
            elif esc == ord('t'):
                out.append(0x09)
            elif esc == ord('0'):
                out.append(0x00)
            elif esc == ord('\\'):
                out.append(0x5C)
            elif esc == ord('"'):
                out.append(0x22)
            elif esc == ord('x') and i + 1 < n:
                hx = s[i:i+2]
                if re.fullmatch(rb"[0-9a-fA-F]{2}", hx):
                    out.append(int(hx, 16))
                    i += 2
                else:
                    out.append(ord('x'))
            else:
                out.append(esc)
        return bytes(out)

    def _extract_magic_strings(self, root: str) -> List[bytes]:
        # Heuristic: strings used in comparisons/magic headers
        src_exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh")
        mags = []
        seen = set()
        str_re = re.compile(rb'"([^"\\]{2,16})"')
        memcmp_re = re.compile(rb"memcmp\s*\([^;]{0,200}?\"([^\"\\]{2,16})\"[^;]{0,200}?\)")
        for p in self._walk_files(root, src_exts):
            data = self._read_file_limited(p, 600_000)
            if not data:
                continue
            for m in memcmp_re.finditer(data):
                s = m.group(1)
                if 2 <= len(s) <= 16 and self._looks_magic(s):
                    if s not in seen:
                        seen.add(s)
                        mags.append(s)
            for m in str_re.finditer(data):
                s = m.group(1)
                if 2 <= len(s) <= 8 and self._looks_magic(s):
                    if s not in seen:
                        seen.add(s)
                        mags.append(s)
        return mags[:64]

    def _looks_magic(self, s: bytes) -> bool:
        if any(ch < 0x20 or ch > 0x7E for ch in s):
            return False
        if b" " in s or b"\t" in s:
            return False
        # Bias towards alnum/underscore/slash/dot
        good = sum((48 <= ch <= 57) or (65 <= ch <= 90) or (97 <= ch <= 122) or ch in b"._-/" for ch in s)
        if good < max(2, int(0.7 * len(s))):
            return False
        # Prefer strings with some uppercase or digits (often magic)
        if not any((65 <= ch <= 90) or (48 <= ch <= 57) for ch in s):
            return False
        return True

    def _collect_sample_inputs(self, root: str) -> List[bytes]:
        exts = (
            ".txt", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini",
            ".dat", ".bin", ".in", ".input", ".conf", ".cfg", ".csv"
        )
        candidates = []
        skip_name = {"cmakelists.txt", "makefile", "license", "copying", "readme", "readme.md", "readme.txt"}
        for p in self._walk_files(root, exts):
            base = os.path.basename(p).lower()
            if base in skip_name:
                continue
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 8192:
                continue
            b = self._read_file_limited(p, 8192)
            if 1 <= len(b) <= 8192:
                candidates.append(b)

        # If nothing, provide a few generic seeds
        if not candidates:
            candidates = [
                b"",
                b"\n",
                b"{}",
                b"[]",
                b'{"a":1,"a":2}',
                b"<a></a>",
                b"a=b\n",
                b"1 2 3\n",
                b"NODE 0\nNODE 0\n",
            ]
        # Dedup
        uniq = []
        seen = set()
        for b in candidates:
            if b in seen:
                continue
            seen.add(b)
            uniq.append(b)
        return uniq[:128]

    # ------------------------ Build ------------------------

    def _build_project(self, root: str, deadline: float) -> List[str]:
        build_dirs = []
        # If a build script exists, try it (but time-box)
        for script in ("build.sh", "compile.sh"):
            sp = os.path.join(root, script)
            if os.path.isfile(sp):
                try:
                    os.chmod(sp, os.stat(sp).st_mode | stat.S_IXUSR)
                except Exception:
                    pass

        # Prefer cmake if present
        if os.path.isfile(os.path.join(root, "CMakeLists.txt")) and time.monotonic() < deadline - 25:
            bd = os.path.join(root, "_build_asan")
            os.makedirs(bd, exist_ok=True)
            env = self._build_env()
            cmake = shutil.which("cmake")
            ninja = shutil.which("ninja")
            if cmake:
                gen = ["-G", "Ninja"] if ninja else []
                cfg = [
                    cmake, "-S", root, "-B", bd,
                    "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                    "-DCMAKE_C_FLAGS=-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer",
                    "-DCMAKE_CXX_FLAGS=-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -std=c++17",
                    "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined",
                ] + gen
                self._run_cmd(cfg, cwd=root, env=env, timeout=max(5.0, deadline - time.monotonic()))
                self._run_cmd([cmake, "--build", bd, "-j", "8"], cwd=root, env=env, timeout=max(5.0, deadline - time.monotonic()))
                build_dirs.append(bd)

        # Try make if present
        if os.path.isfile(os.path.join(root, "Makefile")) and time.monotonic() < deadline - 20:
            env = self._build_env()
            env["CFLAGS"] = env.get("CFLAGS", "") + " -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
            env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -std=c++17"
            env["LDFLAGS"] = env.get("LDFLAGS", "") + " -fsanitize=address,undefined"
            make = shutil.which("make")
            if make:
                self._run_cmd([make, "-j", "8"], cwd=root, env=env, timeout=max(5.0, deadline - time.monotonic()))
                build_dirs.append(root)

        # Fallback: naive compilation if nothing built
        if time.monotonic() < deadline - 15:
            exes = self._find_elf_executables(root)
            if not exes:
                naive = self._naive_compile(root, deadline)
                if naive:
                    build_dirs.append(naive)
        return build_dirs

    def _build_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env.setdefault("CC", "gcc")
        env.setdefault("CXX", "g++")
        env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1:allocator_may_return_null=1"
        env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
        return env

    def _naive_compile(self, root: str, deadline: float) -> Optional[str]:
        gpp = shutil.which("g++")
        if not gpp:
            return None
        # Find candidate main
        srcs = []
        for p in self._walk_files(root, (".cpp", ".cc", ".cxx")):
            if any(seg in p.split(os.sep) for seg in ("test", "tests", "benchmark", "bench", "example", "examples")):
                continue
            srcs.append(p)
        if not srcs:
            return None

        main_candidates = []
        main_re = re.compile(rb"\bint\s+main\s*\(")
        for p in srcs:
            data = self._read_file_limited(p, 400_000)
            if main_re.search(data):
                main_candidates.append(p)

        if not main_candidates:
            # Try libFuzzer entrypoint and create wrapper
            fuzz = []
            fuzz_re = re.compile(rb"\bLLVMFuzzerTestOneInput\s*\(")
            for p in srcs:
                data = self._read_file_limited(p, 400_000)
                if fuzz_re.search(data):
                    fuzz.append(p)
            if fuzz:
                bd = os.path.join(root, "_naive_build")
                os.makedirs(bd, exist_ok=True)
                wrapper = os.path.join(bd, "wrapper_main.cpp")
                with open(wrapper, "wb") as f:
                    f.write(b'#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n')
                    f.write(b'extern "C" int LLVMFuzzerTestOneInput(const uint8_t* Data, size_t Size);\n')
                    f.write(b'int main(){\n')
                    f.write(b'  uint8_t *buf=(uint8_t*)malloc(1<<20);\n')
                    f.write(b'  if(!buf) return 0;\n')
                    f.write(b'  size_t n=fread(buf,1,1<<20,stdin);\n')
                    f.write(b'  (void)LLVMFuzzerTestOneInput(buf,n);\n')
                    f.write(b'  free(buf);\n')
                    f.write(b'  return 0;\n}\n')
                all_srcs = srcs + [wrapper]
                out = os.path.join(bd, "target")
                cmd = [gpp, "-O1", "-g", "-std=c++17", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                       "-I", root, "-o", out] + all_srcs + ["-fsanitize=address,undefined"]
                self._run_cmd(cmd, cwd=root, env=self._build_env(), timeout=max(5.0, deadline - time.monotonic()))
                return bd
            return None

        # If multiple mains, try to compile each separately with all non-main sources (risky); pick first 1-2.
        bd = os.path.join(root, "_naive_build")
        os.makedirs(bd, exist_ok=True)
        non_main = [p for p in srcs if p not in main_candidates]
        # Keep compilation manageable: include only sources under same top-level directories as main
        for idx, mp in enumerate(main_candidates[:2]):
            out = os.path.join(bd, f"target{idx}")
            cmd = [gpp, "-O1", "-g", "-std=c++17", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                   "-I", root, "-o", out, mp] + non_main + ["-fsanitize=address,undefined"]
            try:
                self._run_cmd(cmd, cwd=root, env=self._build_env(), timeout=max(5.0, deadline - time.monotonic()))
            except Exception:
                continue
        return bd

    def _run_cmd(self, cmd: List[str], cwd: str, env: Dict[str, str], timeout: float) -> subprocess.CompletedProcess:
        timeout = max(1.0, min(timeout, 120.0))
        return subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

    # ------------------------ Executable selection ------------------------

    def _find_elf_executables(self, root: str) -> List[str]:
        exes = []
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in {".git", ".svn", ".hg", "__pycache__"} and not d.startswith(".")]
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if st.st_size < 20_000:
                    continue
                if not os.access(p, os.X_OK):
                    continue
                try:
                    with open(p, "rb") as fh:
                        head = fh.read(4)
                    if head != b"\x7fELF":
                        continue
                except Exception:
                    continue
                exes.append(p)
        return exes

    def _dedup_paths(self, paths: List[str]) -> List[str]:
        out = []
        seen = set()
        for p in paths:
            rp = os.path.realpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            out.append(p)
        return out

    def _rank_executables(self, exes: List[str]) -> List[str]:
        def score(p: str) -> Tuple[int, int, int]:
            lp = p.lower()
            s = 0
            for kw, w in (("fuzz", 50), ("pov", 40), ("harness", 40), ("test", -10), ("example", -10), ("demo", -10)):
                if kw in lp:
                    s += w
            # Prefer shorter path and smaller-ish binary (but not tiny)
            try:
                sz = os.stat(p).st_size
            except Exception:
                sz = 10**9
            return (-s, len(p), sz)
        return sorted(exes, key=score)

    # ------------------------ Running and crash detection ------------------------

    def _probe_invocation_mode(self, exe: str, deadline: float) -> Optional[str]:
        if time.monotonic() > deadline - 2:
            return None

        test1 = b"A"
        test2 = b'{"a":1,"a":2}\n'
        modes = ["stdin", "filearg"]
        results = {}
        for m in modes:
            r1 = self._run_target(exe, m, test1, timeout=0.7)
            r2 = self._run_target(exe, m, test2, timeout=0.7)
            results[m] = (r1, r2)

        def usage_like(res: Tuple[int, bytes, bytes]) -> bool:
            rc, out, err = res
            t = (out + b"\n" + err).lower()
            if b"usage" in t or b"usag" in t:
                return True
            if b"invalid option" in t or b"unknown option" in t:
                return True
            if b"requires" in t and b"argument" in t:
                return True
            return False

        def open_fail(res: Tuple[int, bytes, bytes]) -> bool:
            rc, out, err = res
            t = (out + b"\n" + err).lower()
            if b"no such file" in t or b"cannot open" in t or b"failed to open" in t:
                return True
            return False

        # If either mode crashes on probe, accept it
        for m in modes:
            if self._res_is_crash(results[m][0]) or self._res_is_crash(results[m][1]):
                return m

        stdin_u = usage_like(results["stdin"][0]) and usage_like(results["stdin"][1])
        file_u = usage_like(results["filearg"][0]) and usage_like(results["filearg"][1])
        file_openfail = open_fail(results["filearg"][0]) and open_fail(results["filearg"][1])

        if stdin_u and (not file_u) and (not file_openfail):
            return "filearg"
        if file_u and (not stdin_u):
            return "stdin"
        if file_openfail and not stdin_u:
            return "stdin"
        # Default preference: stdin (often simplest)
        return "stdin"

    def _run_target(self, exe: str, mode: str, data: bytes, timeout: float = 0.7) -> Tuple[int, bytes, bytes]:
        env = dict(os.environ)
        env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1:allocator_may_return_null=1"
        env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
        env["MSAN_OPTIONS"] = env.get("MSAN_OPTIONS", "")

        timeout = max(0.1, min(timeout, 2.0))
        try:
            if mode == "stdin":
                p = subprocess.run([exe], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
                return p.returncode, p.stdout, p.stderr
            elif mode == "filearg":
                with tempfile.NamedTemporaryFile(prefix="poc_", delete=False) as tf:
                    tf.write(data)
                    tf.flush()
                    name = tf.name
                try:
                    p = subprocess.run([exe, name], input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
                    return p.returncode, p.stdout, p.stderr
                finally:
                    try:
                        os.unlink(name)
                    except Exception:
                        pass
            else:
                raise ValueError("unknown mode")
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
            err = e.stderr or b""
            return 124, out, err
        except Exception as e:
            return 125, b"", str(e).encode("utf-8", "ignore")

    def _res_is_crash(self, res: Tuple[int, bytes, bytes]) -> bool:
        rc, out, err = res
        if rc == 0 or rc == 124:
            return False
        t = (out + b"\n" + err).lower()
        crash_markers = [
            b"addresssanitizer", b"undefinedbehavior", b"ubsan", b"sanitizer",
            b"double free", b"double-free", b"heap-use-after-free", b"use-after-free",
            b"invalid free", b"free():", b"malloc():", b"corrupted", b"abort",
        ]
        return any(m in t for m in crash_markers)

    def _is_crash(self, exe: str, mode: str, data: bytes, deadline: float) -> bool:
        if time.monotonic() > deadline - 1:
            return False
        res = self._run_target(exe, mode, data, timeout=0.7)
        return self._res_is_crash(res)

    # ------------------------ Fuzzing ------------------------

    def _fuzz_find_crash(
        self,
        exe: str,
        mode: str,
        seeds: List[bytes],
        embedded: List[bytes],
        magics: List[bytes],
        rnd: random.Random,
        deadline: float
    ) -> Optional[bytes]:
        # Deterministic, time-boxed
        begin = time.monotonic()
        local_deadline = min(deadline, begin + 45.0)

        base_seeds = []
        for b in embedded[:16]:
            if 1 <= len(b) <= 2048:
                base_seeds.append(b)
        for b in seeds[:64]:
            if 0 <= len(b) <= 2048:
                base_seeds.append(b)
        if not base_seeds:
            base_seeds = [b"", b"{}"]

        templates = [
            b'{"a":1,"a":2}',
            b'{"a":{"b":1},"a":{"c":2}}',
            b'[{"a":1},{"a":1}]',
            b"<a><b/></a>",
            b"a=b\nc=d\n",
            b"NODE 0\nADD 0 0\n",
            b"node 0\nnode 1\nedge 0 0\n",
            b"1\n1\n1\n",
            b"\x00" * 32,
        ]
        if magics:
            for m in magics[:16]:
                templates.append(m + b"\n")
                templates.append(m + b"\x00" * 8)
                templates.append(m + b" " + b'{"a":1,"a":2}')
                templates.append(m + b" " + b"NODE 0\nNODE 0\n")

        # First, try templates and seeds directly
        for b in base_seeds + templates:
            if time.monotonic() > local_deadline:
                return None
            if self._is_crash(exe, mode, b, local_deadline):
                return b

        # Mutation-based loop
        corpus = list(dict.fromkeys((base_seeds + templates)[:128]))
        max_iters = 3000
        for i in range(max_iters):
            if time.monotonic() > local_deadline:
                break
            seed = corpus[rnd.randrange(len(corpus))]
            cand = self._mutate(seed, magics, rnd)
            if cand is None:
                continue
            if len(cand) > 8192:
                continue
            if self._is_crash(exe, mode, cand, local_deadline):
                return cand
            # Occasionally keep interesting candidates (non-empty and varied)
            if cand and len(corpus) < 256 and rnd.random() < 0.05:
                corpus.append(cand)

        return None

    def _mutate(self, seed: bytes, magics: List[bytes], rnd: random.Random) -> Optional[bytes]:
        if seed is None:
            seed = b""
        b = bytearray(seed)

        ops = []
        ops.append("insert_rand")
        ops.append("delete")
        ops.append("flip")
        ops.append("dup_slice")
        ops.append("wrap_json_dupkey")
        ops.append("wrap_brackets")
        ops.append("repeat_line")
        ops.append("prefix_magic")
        op = ops[rnd.randrange(len(ops))]

        if op == "insert_rand":
            nins = 1 + rnd.randrange(8)
            for _ in range(nins):
                pos = rnd.randrange(len(b) + 1)
                b.insert(pos, rnd.randrange(256))
            return bytes(b)

        if op == "delete":
            if not b:
                return b""
            ndel = 1 + rnd.randrange(min(8, len(b)))
            for _ in range(ndel):
                if not b:
                    break
                pos = rnd.randrange(len(b))
                del b[pos]
            return bytes(b)

        if op == "flip":
            if not b:
                b = bytearray(b"A")
            n = 1 + rnd.randrange(min(8, len(b)))
            for _ in range(n):
                pos = rnd.randrange(len(b))
                b[pos] ^= 1 << rnd.randrange(8)
            return bytes(b)

        if op == "dup_slice":
            if not b:
                b = bytearray(b"{}")
            l = len(b)
            a = rnd.randrange(l)
            c = rnd.randrange(a, min(l, a + 32))
            sl = b[a:c]
            pos = rnd.randrange(l + 1)
            times = 1 + rnd.randrange(6)
            b[pos:pos] = sl * times
            return bytes(b)

        if op == "wrap_json_dupkey":
            key = rnd.choice([b"a", b"key", b"id", b"name", b"n"])
            inner = bytes(b[:64]).replace(b"\x00", b"")  # keep it somewhat printable
            if not inner:
                inner = b"1"
            cand = b'{"' + key + b'":' + inner + b',"'+ key + b'":' + inner + b"}"
            # maybe add nesting
            if rnd.random() < 0.5:
                cand = b'{"x":' + cand + b',"x":' + cand + b"}"
            return cand

        if op == "wrap_brackets":
            inner = bytes(b[:128])
            wrappers = [(b"{", b"}"), (b"[", b"]"), (b"(", b")"), (b"<a>", b"</a>")]
            pre, suf = wrappers[rnd.randrange(len(wrappers))]
            return pre + inner + suf

        if op == "repeat_line":
            # Make many similar lines (could trigger add/duplicate)
            line = b"NODE 0\n" if rnd.random() < 0.5 else b'a=0\n'
            n = 2 + rnd.randrange(40)
            extra = b""
            if rnd.random() < 0.5:
                extra = b"NODE 0 NODE 0\n"
            return (line * n) + extra

        if op == "prefix_magic":
            if not magics:
                return bytes(b)
            m = magics[rnd.randrange(len(magics))]
            sep = rnd.choice([b"", b"\n", b" ", b"\x00"])
            return m + sep + bytes(b)

        return None

    # ------------------------ Minimization ------------------------

    def _minimize(self, exe: str, mode: str, data: bytes, deadline: float) -> bytes:
        data = bytes(data)

        # Quick trims
        data = self._trim_ends(exe, mode, data, deadline)

        # ddmin chunk removal
        data = self._ddmin(exe, mode, data, deadline)

        # Byte deletion pass (time-boxed)
        data = self._byte_delete_pass(exe, mode, data, deadline)

        # Final trim again
        data = self._trim_ends(exe, mode, data, deadline)
        return data

    def _trim_ends(self, exe: str, mode: str, data: bytes, deadline: float) -> bytes:
        if not data:
            return data
        changed = True
        while changed and time.monotonic() < deadline - 1:
            changed = False
            # Trim prefix
            if len(data) > 1:
                d2 = data[1:]
                if self._is_crash(exe, mode, d2, deadline):
                    data = d2
                    changed = True
                    continue
            # Trim suffix
            if len(data) > 1:
                d2 = data[:-1]
                if self._is_crash(exe, mode, d2, deadline):
                    data = d2
                    changed = True
                    continue
        return data

    def _ddmin(self, exe: str, mode: str, data: bytes, deadline: float) -> bytes:
        if len(data) <= 2:
            return data
        n = 2
        while len(data) >= 2 and time.monotonic() < deadline - 1:
            length = len(data)
            chunk = int(math.ceil(length / n))
            if chunk <= 0:
                break
            reduced = False
            for i in range(n):
                if time.monotonic() > deadline - 1:
                    return data
                start = i * chunk
                end = min(length, start + chunk)
                if start >= end:
                    continue
                cand = data[:start] + data[end:]
                if cand and self._is_crash(exe, mode, cand, deadline):
                    data = cand
                    n = max(2, n - 1)
                    reduced = True
                    break
                if not cand:
                    if self._is_crash(exe, mode, cand, deadline):
                        data = cand
                        return data
            if not reduced:
                if n >= length:
                    break
                n = min(length, n * 2)
        return data

    def _byte_delete_pass(self, exe: str, mode: str, data: bytes, deadline: float) -> bytes:
        # O(n^2) worst-case, time-boxed and for small sizes
        if len(data) <= 1:
            return data
        begin = time.monotonic()
        local_deadline = min(deadline, begin + 20.0)
        i = 0
        while i < len(data) and time.monotonic() < local_deadline - 0.5:
            cand = data[:i] + data[i+1:]
            if cand != data and self._is_crash(exe, mode, cand, local_deadline):
                data = cand
                if i > 0:
                    i -= 1
                continue
            i += 1
        return data