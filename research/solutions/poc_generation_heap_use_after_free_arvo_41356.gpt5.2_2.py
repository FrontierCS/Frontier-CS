import os
import re
import io
import sys
import stat
import time
import json
import shlex
import tarfile
import random
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict


class Solution:
    def solve(self, src_path: str) -> bytes:
        random.seed(0)

        with tempfile.TemporaryDirectory(prefix="pocgen_") as td:
            root = Path(td)
            src_root = self._extract_tarball(Path(src_path), root / "src")

            # Collect source text for heuristics
            source_blob = self._read_source_blob(src_root, max_bytes=6_000_000)

            # Heuristic candidate list (no build needed)
            candidates = self._generate_heuristic_candidates(source_blob)

            # Try to build and run to discover a crashing input; if build fails, fall back to heuristics
            build_ok, exe_list = self._build_and_find_executables(src_root)
            if not build_ok or not exe_list:
                return self._pick_best_static_candidate(source_blob, candidates)

            # Limit executables to a few likely targets
            exe_list = exe_list[:6]

            def is_crashing(data: bytes) -> bool:
                for exe in exe_list:
                    crashed, _ = self._run_target(exe, data, timeout=1.0)
                    if crashed:
                        return True
                return False

            # Try heuristic candidates first
            best = None
            for data in candidates:
                if is_crashing(data):
                    best = data
                    break

            # If not found, try structured enumeration and light mutation
            if best is None:
                gen = self._candidate_generator(source_blob)
                start = time.time()
                max_time = 22.0
                max_tries = 1200
                tries = 0
                for data in gen:
                    tries += 1
                    if tries > max_tries or (time.time() - start) > max_time:
                        break
                    if is_crashing(data):
                        best = data
                        break

            if best is None:
                return self._pick_best_static_candidate(source_blob, candidates)

            # Minimize
            best = self._minimize(best, is_crashing, time_budget=10.0)
            return best

    def _extract_tarball(self, tar_path: Path, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)

        def is_within_directory(directory: Path, target: Path) -> bool:
            try:
                directory = directory.resolve()
                target = target.resolve()
            except Exception:
                return False
            return str(target).startswith(str(directory) + os.sep) or target == directory

        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
            safe_members = []
            for m in members:
                name = m.name
                if not name or name.startswith("/") or ".." in Path(name).parts:
                    continue
                dest = out_dir / name
                if not is_within_directory(out_dir, dest):
                    continue
                safe_members.append(m)
            tf.extractall(out_dir, members=safe_members)

        # Determine project root (common pattern: tar contains single top-level dir)
        children = [p for p in out_dir.iterdir() if p.name not in (".", "..")]
        if len(children) == 1 and children[0].is_dir():
            return children[0]
        return out_dir

    def _read_source_blob(self, src_root: Path, max_bytes: int = 6_000_000) -> str:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inl", ".ipp", ".txt", ".md", ".rst"}
        total = 0
        parts = []
        for p in src_root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in exts:
                continue
            try:
                b = p.read_bytes()
            except Exception:
                continue
            if not b:
                continue
            if total + len(b) > max_bytes:
                b = b[: max(0, max_bytes - total)]
            total += len(b)
            if not b:
                break
            try:
                s = b.decode("utf-8", "replace")
            except Exception:
                s = str(b)
            parts.append(s)
            if total >= max_bytes:
                break
        return "\n".join(parts)

    def _build_and_find_executables(self, src_root: Path) -> Tuple[bool, List[Path]]:
        # Try CMake first
        build_root = src_root / "_poc_build"
        if build_root.exists():
            shutil.rmtree(build_root, ignore_errors=True)
        build_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "detect_leaks=0:halt_on_error=1:allocator_may_return_null=1")
        env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")

        cmake_lists = src_root / "CMakeLists.txt"
        ok = False

        cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
        cxxflags = cflags
        ldflags = "-fsanitize=address"

        if cmake_lists.exists() and shutil.which("cmake"):
            gen_args = []
            if shutil.which("ninja"):
                gen_args = ["-G", "Ninja"]
            cfg_cmd = [
                "cmake",
                "-S",
                str(src_root),
                "-B",
                str(build_root),
                *gen_args,
                "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                f"-DCMAKE_C_FLAGS={cflags}",
                f"-DCMAKE_CXX_FLAGS={cxxflags}",
                f"-DCMAKE_EXE_LINKER_FLAGS={ldflags}",
            ]
            ok = self._run_cmd(cfg_cmd, cwd=src_root, env=env, timeout=180.0)
            if ok:
                ok = self._run_cmd(["cmake", "--build", str(build_root), "-j", "8"], cwd=src_root, env=env, timeout=240.0)
            if ok:
                exes = self._find_executables(build_root)
                if exes:
                    return True, exes

        # Try Makefile
        makefile = src_root / "Makefile"
        if makefile.exists() and shutil.which("make"):
            env2 = env.copy()
            env2["CFLAGS"] = (env2.get("CFLAGS", "") + " " + cflags).strip()
            env2["CXXFLAGS"] = (env2.get("CXXFLAGS", "") + " " + cxxflags).strip()
            env2["LDFLAGS"] = (env2.get("LDFLAGS", "") + " " + ldflags).strip()
            ok = self._run_cmd(["make", "-j", "8"], cwd=src_root, env=env2, timeout=240.0)
            if ok:
                exes = self._find_executables(src_root)
                if exes:
                    return True, exes

        # Fallback: compile all .cpp into one binary if feasible
        gpp = shutil.which("g++") or shutil.which("clang++")
        if gpp:
            cpp_files = [p for p in src_root.rglob("*.cpp")]
            if not cpp_files:
                cpp_files = [p for p in src_root.rglob("*.cc")] + [p for p in src_root.rglob("*.cxx")]
            main_files = []
            for p in cpp_files:
                try:
                    s = p.read_text(errors="ignore")
                except Exception:
                    continue
                if "int main" in s:
                    main_files.append(p)
            # Compile everything (may fail), but usually small projects
            if cpp_files and main_files:
                out_exe = build_root / "poc_target"
                cmd = [gpp, "-std=c++17", *shlex.split(cxxflags), *map(str, cpp_files), "-o", str(out_exe), *shlex.split(ldflags)]
                ok = self._run_cmd(cmd, cwd=src_root, env=env, timeout=240.0)
                if ok and out_exe.exists():
                    out_exe.chmod(out_exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    return True, [out_exe]

        return False, []

    def _run_cmd(self, cmd: List[str], cwd: Path, env: Dict[str, str], timeout: float) -> bool:
        try:
            p = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            return p.returncode == 0
        except Exception:
            return False

    def _find_executables(self, root: Path) -> List[Path]:
        exes = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if name.endswith((".a", ".o", ".so", ".dylib", ".dll", ".cmake")):
                continue
            try:
                st = p.stat()
            except Exception:
                continue
            if st.st_size < 10_000:
                continue
            if os.access(p, os.X_OK):
                exes.append(p)
        # Sort by size descending, then by path length
        exes.sort(key=lambda x: (-x.stat().st_size, len(str(x))))
        # De-duplicate by basename (keep largest)
        seen = set()
        filtered = []
        for e in exes:
            bn = e.name
            if bn in seen:
                continue
            seen.add(bn)
            filtered.append(e)
        return filtered

    def _run_target(self, exe: Path, data: bytes, timeout: float = 1.0) -> Tuple[bool, str]:
        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "detect_leaks=0:halt_on_error=1:allocator_may_return_null=1")
        env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")

        def classify(p: subprocess.CompletedProcess) -> Tuple[bool, str]:
            out = b""
            try:
                out = (p.stdout or b"") + b"\n" + (p.stderr or b"")
            except Exception:
                pass
            s = ""
            try:
                s = out.decode("utf-8", "replace")
            except Exception:
                s = repr(out)
            crashed = False
            if p.returncode < 0:
                crashed = True
            else:
                low = s.lower()
                if "addresssanitizer" in low or "heap-use-after-free" in low or "double-free" in low or "use-after-free" in low:
                    crashed = True
            return crashed, s

        # Try stdin mode
        try:
            p = subprocess.run(
                [str(exe)],
                input=data,
                cwd=str(exe.parent),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            crashed, s = classify(p)
            if crashed:
                return True, s
            # If looks like missing filename argument, try file mode
            combo = ((p.stdout or b"") + b"\n" + (p.stderr or b"")).decode("utf-8", "replace").lower()
            wants_file = ("usage" in combo or "argument" in combo or "filename" in combo or "file" in combo) and (p.returncode != 0)
            if not wants_file:
                return False, s
        except subprocess.TimeoutExpired:
            wants_file = True
        except Exception:
            wants_file = True

        if wants_file:
            try:
                with tempfile.NamedTemporaryFile(prefix="poc_", suffix=".bin", delete=False) as tf:
                    tf.write(data)
                    tf.flush()
                    tmpname = tf.name
                try:
                    p2 = subprocess.run(
                        [str(exe), tmpname],
                        input=b"",
                        cwd=str(exe.parent),
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=timeout,
                    )
                    crashed, s2 = classify(p2)
                    return crashed, s2
                finally:
                    try:
                        os.unlink(tmpname)
                    except Exception:
                        pass
            except Exception:
                return False, ""
        return False, ""

    def _generate_heuristic_candidates(self, source_blob: str) -> List[bytes]:
        blob_low = source_blob.lower()

        cands = []

        # Generic minimal candidates
        cands.append(b"")
        cands.append(b"\n")
        cands.append(b"0\n")
        cands.append(b"A\n")

        # Command-style duplicates
        cmd_adds = [b"add", b"ADD", b"insert", b"INSERT", b"push", b"PUSH", b"append", b"APPEND", b"node", b"NODE"]
        ids = [b"a", b"A", b"0", b"1", b"key", b"name"]
        for cmd in cmd_adds:
            for ident in ids:
                cands.append(cmd + b" " + ident + b"\n" + cmd + b" " + ident + b"\n")
                cands.append(cmd + b"\n" + cmd + b"\n")
                cands.append(cmd + b" " + ident + b" " + ident + b"\n" + cmd + b" " + ident + b" " + ident + b"\n")

        # INI duplicates
        cands.append(b"[s]\na=1\na=2\n")
        cands.append(b"a=1\na=2\n")
        cands.append(b"[x]\nkey=1\nkey=2\n")

        # YAML duplicates
        cands.append(b"a: 1\na: 2\n")
        cands.append(b"root:\n  a: 1\n  a: 2\n")

        # JSON duplicates
        json_dup = [
            b'{"a":0,"a":0}',
            b'{"a":0,"b":0,"a":1}',
            b'{"a":{"b":0},"a":{"b":1}}',
            b'{"a":[1,2,3],"a":[4]}',
            b'{"a":0,"a":0,"a":0,"a":0}',
        ]
        cands.extend(json_dup)

        # XML duplicates (attributes)
        cands.append(b'<a x="1" x="2"></a>\n')
        cands.append(b'<root><a/><a/></root>\n')

        # If hints suggest a specific format, push those earlier by reordering
        pri = []
        if "json" in blob_low:
            pri.extend(json_dup)
        if "yaml" in blob_low:
            pri.extend([b"a: 1\na: 2\n", b"root:\n  a: 1\n  a: 2\n"])
        if "toml" in blob_low or "ini" in blob_low:
            pri.extend([b"a=1\na=2\n", b"[s]\na=1\na=2\n"])
        if "xml" in blob_low or "html" in blob_low:
            pri.extend([b'<a x="1" x="2"></a>\n', b'<root><a/><a/></root>\n'])

        # Dedup preserve order, with pri at front
        merged = pri + cands
        out = []
        seen = set()
        for b in merged:
            if b not in seen:
                seen.add(b)
                out.append(b)
        return out

    def _candidate_generator(self, source_blob: str):
        blob_low = source_blob.lower()
        # JSON repeated key "a"
        for n in range(2, 60):
            obj = b"{" + b",".join([b'"a":0'] * n) + b"}"
            yield obj
            # with commas and spaces
            obj2 = b"{" + b", ".join([b'"a":0'] * n) + b"}\n"
            yield obj2
            if len(obj) > 4096:
                break

        # JSON nested repeated key
        for depth in range(1, 12):
            inner = b"0"
            for _ in range(depth):
                inner = b'{"a":' + inner + b',"a":' + inner + b"}"
            yield inner
            yield inner + b"\n"

        # INI / TOML repeated keys
        for n in range(2, 80):
            lines = [f"a={i}".encode() for i in range(n)]
            lines.insert(0, b"[s]")
            yield b"\n".join(lines) + b"\n"
            if n >= 8:
                # repeated same key
                lines2 = [b"[s]"] + [b"a=1"] * n
                yield b"\n".join(lines2) + b"\n"

        # YAML repeated keys
        for n in range(2, 80):
            yield (b"a: 1\n" * (n - 1)) + b"a: 2\n"
            if n >= 4:
                yield b"root:\n" + (b"  a: 1\n" * (n - 1)) + b"  a: 2\n"

        # Command-like from extracted tokens
        tokens = self._extract_command_tokens(source_blob)
        add_like = [t for t in tokens if "add" in t.lower() or "insert" in t.lower() or "push" in t.lower() or "append" in t.lower()]
        if not add_like:
            add_like = ["add", "ADD", "insert", "push"]

        ids = ["a", "A", "0", "1", "key", "name", "x", "y", "z"]
        for cmd in add_like[:20]:
            cmd_b = cmd.encode("utf-8", "ignore")[:16] or b"add"
            for ident in ids:
                ident_b = ident.encode()
                yield cmd_b + b" " + ident_b + b"\n" + cmd_b + b" " + ident_b + b"\n"
                yield cmd_b + b" " + ident_b + b" " + ident_b + b"\n" + cmd_b + b" " + ident_b + b" " + ident_b + b"\n"
                for n in (3, 4, 6, 8, 12):
                    yield (cmd_b + b" " + ident_b + b"\n") * (n - 1) + (cmd_b + b" " + ident_b + b"\n")

        # Light random mutation over a few likely formats
        bases = [
            b'{"a":0,"a":0}',
            b'a=1\na=2\n',
            b"a: 1\na: 2\n",
            b"add a\nadd a\n",
            b'<a x="1" x="2"></a>\n',
        ]
        for i in range(600):
            base = random.choice(bases)
            data = bytearray(base)
            # random insertions / duplications
            if random.random() < 0.6:
                ins = random.randint(0, len(data))
                frag = random.choice([b"a", b"0", b"1", b'"a":0,', b"add a\n", b"a=1\n", b"a: 1\n", b"x=\"1\" ", b",", b"\n"])
                data[ins:ins] = frag
            if random.random() < 0.4 and len(data) > 5:
                a = random.randint(0, len(data) - 1)
                b = random.randint(a, min(len(data), a + random.randint(1, 12)))
                del data[a:b]
            if random.random() < 0.2:
                data += random.choice([b"\n", b"}", b"}\n", b"\x00"])
            yield bytes(data)

        # Try a small binary-ish header candidates
        for n in range(8, 128, 8):
            yield (b"\x00" * (n - 4)) + b"\x01\x00\x00\x00"
            yield (b"\xff" * n)

        # If hints show JSON strongly, try duplicate keys with varying names
        if "json" in blob_low or "nlohmann" in blob_low or "rapidjson" in blob_low:
            keys = [b"a", b"aa", b"key", b"name", b"id"]
            for k in keys:
                for n in range(2, 40):
                    pair = b'"' + k + b'":0'
                    yield b"{" + b",".join([pair] * n) + b"}"

    def _extract_command_tokens(self, source_blob: str) -> List[str]:
        tokens = set()

        # Capture literals used in comparisons or dispatch
        patterns = [
            r'==\s*"([^"\\]{1,24})"',
            r'!=\s*"([^"\\]{1,24})"',
            r'strcmp\s*\(\s*[^,]+,\s*"([^"\\]{1,24})"\s*\)',
            r'compare\s*\(\s*"([^"\\]{1,24})"\s*\)',
            r'case\s*\'([A-Za-z0-9])\'',
        ]
        for pat in patterns:
            for m in re.finditer(pat, source_blob):
                g = m.group(1)
                if not g:
                    continue
                if len(g) == 1 and pat.startswith("case"):
                    tokens.add(g)
                    continue
                if any(ch in g for ch in "\r\n\t"):
                    continue
                if len(g) <= 24:
                    tokens.add(g)

        # Filter to likely command tokens
        out = []
        for t in tokens:
            if len(t) == 0 or len(t) > 24:
                continue
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-]{0,23}", t):
                out.append(t)
        out.sort(key=lambda x: (len(x), x.lower()))
        return out

    def _pick_best_static_candidate(self, source_blob: str, candidates: List[bytes]) -> bytes:
        blob_low = source_blob.lower()
        # Choose based on hints
        if "json" in blob_low or "nlohmann" in blob_low or "rapidjson" in blob_low:
            return b'{"a":0,"a":0,"a":0,"a":0,"a":0,"a":0}\n'
        if "yaml" in blob_low:
            return b"a: 1\na: 2\na: 3\na: 4\na: 5\na: 6\n"
        if "toml" in blob_low or "ini" in blob_low:
            return b"[s]\na=1\na=2\na=3\na=4\na=5\na=6\n"
        if "xml" in blob_low or "html" in blob_low:
            return b'<a x="1" x="2" x="3" x="4" x="5"></a>\n'
        # Otherwise command-style
        return b"add a\nadd a\nadd a\nadd a\n"

    def _minimize(self, data: bytes, is_crashing, time_budget: float = 10.0) -> bytes:
        start = time.time()

        def time_left() -> float:
            return time_budget - (time.time() - start)

        if not is_crashing(data):
            return data

        # Trim common trailing whitespace/nulls where possible
        for _ in range(4):
            if time_left() <= 0:
                return data
            d2 = data.rstrip(b"\x00 \t\r\n")
            if d2 != data and d2 and is_crashing(d2):
                data = d2
            else:
                break

        # Try line-based minimization if mostly text
        is_texty = self._is_probably_text(data)
        if is_texty and (b"\n" in data or b"\r" in data) and time_left() > 0:
            data = self._minimize_by_lines(data, is_crashing, time_left)

        # Byte-level ddmin with bounded steps
        if time_left() > 0:
            data = self._ddmin_bytes(data, is_crashing, time_left, max_tests=220)

        # Final trailing trim
        if time_left() > 0:
            d2 = data.rstrip(b"\x00 \t\r\n")
            if d2 != data and d2 and is_crashing(d2):
                data = d2

        return data

    def _is_probably_text(self, data: bytes) -> bool:
        if not data:
            return True
        printable = 0
        for b in data[:512]:
            if b in (9, 10, 13) or 32 <= b <= 126:
                printable += 1
        return printable / min(len(data), 512) > 0.85

    def _minimize_by_lines(self, data: bytes, is_crashing, time_left_fn) -> bytes:
        # Preserve line endings by splitting with keepends
        try:
            s = data.decode("utf-8", "replace")
            bdata = s.encode("utf-8", "ignore")
            # If re-encoding changes too much, just operate on bytes
            if len(bdata) < max(1, len(data) // 2):
                lines = data.splitlines(keepends=True)
            else:
                lines = data.splitlines(keepends=True)
        except Exception:
            lines = data.splitlines(keepends=True)

        if len(lines) <= 1:
            return data

        changed = True
        while changed and time_left_fn() > 0:
            changed = False
            for i in range(len(lines)):
                if time_left_fn() <= 0:
                    return b"".join(lines)
                trial = b"".join(lines[:i] + lines[i + 1 :])
                if trial and is_crashing(trial):
                    lines = lines[:i] + lines[i + 1 :]
                    changed = True
                    break
        return b"".join(lines)

    def _ddmin_bytes(self, data: bytes, is_crashing, time_left_fn, max_tests: int = 220) -> bytes:
        if len(data) <= 1:
            return data
        if not is_crashing(data):
            return data

        tests = 0
        n = 2
        cur = data

        while len(cur) >= 2 and time_left_fn() > 0 and tests < max_tests:
            chunk = (len(cur) + n - 1) // n
            if chunk <= 0:
                break

            reduced = False
            for i in range(0, len(cur), chunk):
                if time_left_fn() <= 0 or tests >= max_tests:
                    return cur
                trial = cur[:i] + cur[i + chunk :]
                tests += 1
                if trial and is_crashing(trial):
                    cur = trial
                    n = max(2, n - 1)
                    reduced = True
                    break

            if not reduced:
                if n >= len(cur):
                    break
                n = min(len(cur), n * 2)

        return cur