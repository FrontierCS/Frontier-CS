import os
import re
import sys
import tarfile
import tempfile
import subprocess
import time
import random
import struct
from pathlib import Path
from typing import List, Tuple, Optional, Set, Dict


class Solution:
    def __init__(self):
        self._rng = random.Random(1337)
        self._prog_path: Optional[str] = None
        self._cwd: Optional[str] = None
        self._use_file: bool = False
        self._timeout = 0.6
        self._tokens: List[bytes] = []
        self._binary_mode: bool = False

    def _safe_extract_tar(self, tar_path: str, dst: str) -> None:
        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                member_path = os.path.join(dst, member.name)
                if not is_within_directory(dst, member_path):
                    continue
                try:
                    tf.extract(member, dst)
                except Exception:
                    pass

    def _find_project_root(self, tmpdir: str) -> str:
        entries = [p for p in Path(tmpdir).iterdir() if p.name not in (".", "..")]
        dirs = [p for p in entries if p.is_dir()]
        if len(dirs) == 1 and all(not p.is_file() for p in entries if p != dirs[0]):
            return str(dirs[0])
        return tmpdir

    def _read_text(self, path: str, max_bytes: int = 2_000_000) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _collect_sources(self, root: str) -> List[str]:
        ex_dirs = {"test", "tests", "testing", "benchmark", "benchmarks", "examples", "example", "fuzz", "fuzzer", "third_party", "thirdparty", ".git"}
        srcs = []
        for p in Path(root).rglob("*"):
            if not p.is_file():
                continue
            lp = str(p).lower()
            parts = {x.lower() for x in p.parts}
            if parts & ex_dirs:
                continue
            if p.suffix.lower() in (".c", ".cc", ".cpp", ".cxx", ".c++"):
                srcs.append(str(p))
        return srcs

    def _detect_main_files(self, srcs: List[str]) -> List[str]:
        mains = []
        main_re = re.compile(r"\bint\s+main\s*\(", re.M)
        for s in srcs:
            txt = self._read_text(s)
            if main_re.search(txt):
                mains.append(s)
        return mains

    def _extract_tokens_from_sources(self, srcs: List[str]) -> Tuple[List[bytes], bool, Dict[str, int]]:
        tokens: Set[bytes] = set()
        binary_mode = False
        style: Dict[str, int] = {"json": 0, "xml": 0, "newick": 0, "cmd": 0, "binary": 0, "paren": 0}
        strlit_re = re.compile(r"\"((?:\\.|[^\"\\])*)\"")
        cmp_re = re.compile(r"(?:==\s*\"([^\"]+)\"|strcmp\s*\([^,]+,\s*\"([^\"]+)\"\s*\))")
        for s in srcs:
            txt = self._read_text(s)
            if not txt:
                continue
            if ("istream::read" in txt) or (".read(" in txt) or ("fread(" in txt) or ("read(" in txt and "std::cin" in txt):
                binary_mode = True
                style["binary"] += 1
            for m in strlit_re.finditer(txt):
                val = m.group(1)
                if not val:
                    continue
                low = val.lower()
                if "json" in low:
                    style["json"] += 2
                if "xml" in low:
                    style["xml"] += 2
                if "newick" in low or "phylo" in low or "tree" in low:
                    style["newick"] += 2
                if "expected ')'" in low or "expected )" in low or "expected ','" in low or "expected ," in low:
                    style["paren"] += 2
                if "usage" in low or "command" in low:
                    style["cmd"] += 1

                if 1 <= len(val) <= 24:
                    if any(c in val for c in "\n\r\t"):
                        continue
                    b = val.encode("utf-8", errors="ignore")
                    if b:
                        tokens.add(b)

            for m in cmp_re.finditer(txt):
                v = m.group(1) or m.group(2)
                if not v:
                    continue
                low = v.lower()
                if low in ("add", "insert", "remove", "delete", "del", "push", "pop", "new", "free", "node", "child", "parent", "set", "get", "put"):
                    style["cmd"] += 3
                if 1 <= len(v) <= 24:
                    tokens.add(v.encode("utf-8", errors="ignore"))

            if "Node::add" in txt or "::add(" in txt:
                style["cmd"] += 1
            if "(" in txt and ")" in txt and "," in txt:
                style["paren"] += 1

        common = [
            b"add", b"ADD", b"insert", b"remove", b"delete", b"del",
            b"node", b"child", b"parent", b"root", b"tree",
            b"\n", b" ", b"\t", b",", b";", b"(", b")", b"{", b"}", b"[", b"]", b":", b"\"",
        ]
        for c in common:
            tokens.add(c)
        tok_list = sorted(tokens, key=lambda x: (len(x), x))[:400]
        return tok_list, binary_mode, style

    def _compile_with_gxx(self, root: str, srcs: List[str], main_file: Optional[str], out_path: str) -> bool:
        if not srcs:
            return False
        use_srcs = list(srcs)
        if main_file:
            mains = self._detect_main_files(srcs)
            for mf in mains:
                if mf != main_file and mf in use_srcs:
                    use_srcs.remove(mf)

        cxx = os.environ.get("CXX", "g++")
        flags_base = [
            "-O1", "-g",
            "-fsanitize=address",
            "-fno-omit-frame-pointer",
            "-fno-sanitize-recover=all",
        ]
        includes = ["-I", root]
        stds = ["-std=c++17", "-std=gnu++17", "-std=c++20", "-std=gnu++20"]
        extras = [
            [],
            ["-pthread"],
            ["-pthread", "-Wno-narrowing", "-Wno-sign-compare", "-Wno-unused-result"],
        ]

        for std in stds:
            for extra in extras:
                cmd = [cxx, std] + flags_base + extra + includes + use_srcs + ["-o", out_path]
                try:
                    r = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                    if r.returncode == 0 and os.path.exists(out_path):
                        return True
                except Exception:
                    continue
        return False

    def _compile_with_clangxx(self, root: str, srcs: List[str], main_file: Optional[str], out_path: str) -> bool:
        if not srcs:
            return False
        use_srcs = list(srcs)
        if main_file:
            mains = self._detect_main_files(srcs)
            for mf in mains:
                if mf != main_file and mf in use_srcs:
                    use_srcs.remove(mf)

        clang = "clang++"
        try:
            subprocess.run([clang, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        except Exception:
            return False

        flags_base = [
            "-O1", "-g",
            "-fsanitize=address",
            "-fno-omit-frame-pointer",
            "-fno-sanitize-recover=all",
        ]
        includes = ["-I", root]
        stds = ["-std=c++17", "-std=gnu++17", "-std=c++20", "-std=gnu++20"]
        extras = [
            [],
            ["-pthread"],
            ["-pthread", "-Wno-narrowing", "-Wno-sign-compare", "-Wno-unused-result"],
        ]

        for std in stds:
            for extra in extras:
                cmd = [clang, std] + flags_base + extra + includes + use_srcs + ["-o", out_path]
                try:
                    r = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                    if r.returncode == 0 and os.path.exists(out_path):
                        return True
                except Exception:
                    continue
        return False

    def _build_program(self, root: str) -> Optional[str]:
        srcs = self._collect_sources(root)
        if not srcs:
            return None
        mains = self._detect_main_files(srcs)
        main_file = mains[0] if mains else None

        out_path = os.path.join(root, "poc_prog_asan")
        ok = self._compile_with_gxx(root, srcs, main_file, out_path)
        if not ok:
            ok = self._compile_with_clangxx(root, srcs, main_file, out_path)
        if ok:
            try:
                os.chmod(out_path, 0o755)
            except Exception:
                pass
            return out_path

        return None

    def _decide_input_mode(self, prog: str, root: str, main_file: Optional[str]) -> bool:
        txt = self._read_text(main_file) if main_file else ""
        if "argv[1]" in txt or "argc" in txt and ("< 2" in txt or "<= 1" in txt):
            return True

        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1:abort_on_error=1"
        env["UBSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1"
        try:
            r = subprocess.run([prog], cwd=root, input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=0.4)
            out = (r.stdout + r.stderr).decode("utf-8", errors="ignore").lower()
            if "usage" in out and ("file" in out or "path" in out or "argv" in out):
                return True
        except Exception:
            pass
        return False

    def _run(self, data: bytes) -> Tuple[int, bytes, bytes]:
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1:abort_on_error=1:allocator_may_return_null=1"
        env["UBSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1"
        env["MSAN_OPTIONS"] = env.get("MSAN_OPTIONS", "")
        try:
            if self._use_file:
                with tempfile.NamedTemporaryFile(prefix="poc_in_", delete=False) as f:
                    f.write(data)
                    f.flush()
                    in_path = f.name
                try:
                    r = subprocess.run([self._prog_path, in_path], cwd=self._cwd, input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=self._timeout)
                    return r.returncode, r.stdout, r.stderr
                finally:
                    try:
                        os.unlink(in_path)
                    except Exception:
                        pass
            else:
                r = subprocess.run([self._prog_path], cwd=self._cwd, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=self._timeout)
                return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
            err = e.stderr or b""
            return 124, out, err
        except Exception as e:
            return 125, b"", (str(e).encode("utf-8", errors="ignore"))

    def _is_target_crash(self, rc: int, err: bytes) -> bool:
        if rc == 0 or rc == 124:
            return False
        s = err.decode("utf-8", errors="ignore").lower()
        if "addresssanitizer" not in s and "asan" not in s:
            return False
        if ("double-free" in s) or ("attempting double-free" in s) or ("heap-use-after-free" in s) or ("use-after-free" in s) or ("invalid free" in s):
            return True
        if ("free" in s and "previously freed" in s) or ("freed heap region" in s):
            return True
        return False

    def _mutate(self, data: bytes) -> bytes:
        if len(data) == 0:
            data = b"\n"
        op = self._rng.randrange(0, 10)
        b = bytearray(data)

        if op == 0:
            pos = self._rng.randrange(0, len(b))
            b[pos] ^= 1 << self._rng.randrange(0, 8)
            return bytes(b)
        if op == 1:
            pos = self._rng.randrange(0, len(b) + 1)
            ins = self._rng.randrange(0, 256)
            b[pos:pos] = bytes([ins])
            return bytes(b)
        if op == 2:
            if len(b) > 1:
                pos = self._rng.randrange(0, len(b))
                del b[pos]
            return bytes(b)
        if op == 3:
            pos = self._rng.randrange(0, len(b) + 1)
            ln = self._rng.randrange(1, 9)
            chunk = bytes(self._rng.randrange(0, 256) for _ in range(ln))
            b[pos:pos] = chunk
            return bytes(b)
        if op == 4:
            if self._tokens:
                tok = self._rng.choice(self._tokens)
            else:
                tok = b"add"
            pos = self._rng.randrange(0, len(b) + 1)
            b[pos:pos] = tok
            return bytes(b)
        if op == 5:
            if len(b) > 4:
                i = self._rng.randrange(0, len(b) - 1)
                j = self._rng.randrange(i + 1, min(len(b), i + 32))
                del b[i:j]
            return bytes(b)
        if op == 6:
            if self._tokens:
                tok = self._rng.choice(self._tokens)
            else:
                tok = b"\n"
            b.extend(tok)
            return bytes(b)
        if op == 7:
            if len(b) > 8:
                pos = self._rng.randrange(0, len(b) - 4)
                val = self._rng.getrandbits(32)
                b[pos:pos + 4] = struct.pack("<I", val)
            else:
                b.extend(struct.pack("<I", self._rng.getrandbits(32)))
            return bytes(b)
        if op == 8:
            if self._tokens:
                t1 = self._rng.choice(self._tokens)
                t2 = self._rng.choice(self._tokens)
                pos = self._rng.randrange(0, len(b) + 1)
                b[pos:pos] = t1 + b" " + t2 + b"\n"
            else:
                b.extend(b"\n")
            return bytes(b)
        if op == 9:
            if len(b) > 1:
                i = self._rng.randrange(0, len(b))
                j = self._rng.randrange(0, len(b))
                if i > j:
                    i, j = j, i
                b[i:j] = b[i:j][::-1]
            return bytes(b)

        return bytes(b)

    def _ddmin(self, data: bytes, test_fn, max_time: float) -> bytes:
        start = time.monotonic()
        if not test_fn(data):
            return data
        n = 2
        cur = data
        while len(cur) >= 2 and time.monotonic() - start < max_time:
            chunk_len = max(1, len(cur) // n)
            reduced = False
            i = 0
            while i < len(cur) and time.monotonic() - start < max_time:
                j = min(len(cur), i + chunk_len)
                cand = cur[:i] + cur[j:]
                if cand and test_fn(cand):
                    cur = cand
                    reduced = True
                    n = max(2, n - 1)
                    break
                i = j
            if not reduced:
                if n >= len(cur):
                    break
                n = min(len(cur), n * 2)
        if time.monotonic() - start < max_time:
            i = 0
            while i < len(cur) and time.monotonic() - start < max_time:
                cand = cur[:i] + cur[i + 1:]
                if cand and test_fn(cand):
                    cur = cand
                else:
                    i += 1
        return cur

    def _gen_newick(self, children: int) -> bytes:
        # Create a node with many children; a binary-tree parser might throw on >2
        names = [b"a", b"b", b"c", b"d", b"e", b"f", b"g", b"h", b"i", b"j"]
        self._rng.shuffle(names)
        parts = []
        for i in range(children):
            nm = names[i % len(names)]
            if self._rng.random() < 0.2:
                nm = nm + str(self._rng.randrange(0, 100)).encode()
            parts.append(nm)
        s = b"(" + b",".join(parts) + b");\n"
        return s

    def _gen_json_dup(self) -> bytes:
        # Duplicate keys might trigger exception during insertion into a node/map
        k = b"a"
        if self._rng.random() < 0.3:
            k = b"key"
        v1 = str(self._rng.randrange(0, 10)).encode()
        v2 = str(self._rng.randrange(0, 10)).encode()
        return b'{"' + k + b'":' + v1 + b',"' + k + b'":' + v2 + b'}\n'

    def _gen_cmd_script(self, cmd_add: bytes) -> bytes:
        # Script-like inputs: repeat adds to overflow constraint or create duplicate
        names = [b"a", b"b", b"c", b"d", b"e"]
        self._rng.shuffle(names)
        lines = []
        for i in range(6):
            a = names[i % len(names)]
            b = names[(i + 1) % len(names)]
            if self._rng.random() < 0.35:
                b = a
            if self._rng.random() < 0.2:
                a = str(self._rng.randrange(0, 5)).encode()
            if self._rng.random() < 0.2:
                b = str(self._rng.randrange(0, 5)).encode()
            lines.append(cmd_add + b" " + a + b" " + b)
        return b"\n".join(lines) + b"\n"

    def _gen_binary_guess(self) -> bytes:
        # Heuristic binary structure: [count][(parent,name_len,name)*]
        cnt = self._rng.randrange(3, 10)
        out = bytearray()
        out += struct.pack("<I", cnt)
        for i in range(cnt):
            parent = self._rng.randrange(0, max(1, i))
            name = (b"A" * self._rng.randrange(1, 9)) + bytes([self._rng.randrange(48, 58)])
            out += struct.pack("<I", parent)
            out += struct.pack("<I", len(name))
            out += name
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="poc_build_") as td:
            self._safe_extract_tar(src_path, td)
            root = self._find_project_root(td)

            srcs = self._collect_sources(root)
            mains = self._detect_main_files(srcs)
            main_file = mains[0] if mains else None

            self._tokens, self._binary_mode, style = self._extract_tokens_from_sources(srcs)

            prog = self._build_program(root)
            if not prog:
                # Fallback: common patterns (60-ish bytes)
                return (b"(a,b,c,d,e,f,g,h,i,j);\n" * 2)[:60]

            self._prog_path = prog
            self._cwd = root
            self._use_file = self._decide_input_mode(prog, root, main_file)

            cmd_add = b"add"
            for t in self._tokens:
                if t.lower() == b"add":
                    cmd_add = t
                    break
            if cmd_add.lower() != b"add":
                for t in self._tokens:
                    if t.lower() in (b"insert", b"push", b"put", b"append"):
                        cmd_add = t
                        break

            def test_crash(d: bytes) -> bool:
                rc, out, err = self._run(d)
                return self._is_target_crash(rc, err)

            seeds: List[bytes] = []
            seeds.extend([b"", b"\n", b"0\n", b"1\n", b"2\n", b"3\n"])
            seeds.append(self._gen_json_dup())
            seeds.append(b'{"a":1,"a":2}\n')
            seeds.append(b'{"a":{"b":1},"a":{"c":2}}\n')
            seeds.append(b"<a><b/></a>\n")
            seeds.append(b"<a><b></b><b></b><b></b></a>\n")
            seeds.append(b"(a,b,c);\n")
            seeds.append(b"(a,b,c,d);\n")
            seeds.append(self._gen_newick(3))
            seeds.append(self._gen_newick(4))
            seeds.append(self._gen_newick(8))
            seeds.append(self._gen_cmd_script(cmd_add))
            seeds.append((cmd_add + b" a b\n" + cmd_add + b" a c\n" + cmd_add + b" a d\n"))
            if self._binary_mode:
                for _ in range(10):
                    seeds.append(self._gen_binary_guess())
            # Add keyword-heavy seed
            kw = []
            for t in self._tokens:
                tl = t.lower()
                if tl.isalpha() and 2 <= len(tl) <= 8:
                    kw.append(tl)
                if len(kw) >= 12:
                    break
            if kw:
                seeds.append(b" ".join(kw) + b"\n" + b" ".join(kw[::-1]) + b"\n")

            for sd in seeds:
                if len(sd) == 0:
                    continue
                if test_crash(sd):
                    minimized = self._ddmin(sd, test_crash, max_time=6.0)
                    return minimized

            corpus: List[bytes] = [s for s in seeds if s]
            if not corpus:
                corpus = [b"\n"]

            start = time.monotonic()
            time_budget = 24.0
            best_crash: Optional[bytes] = None

            seen: Set[int] = set()
            it = 0
            while time.monotonic() - start < time_budget:
                it += 1
                if it % 25 == 0 and (time.monotonic() - start) < time_budget * 0.5:
                    if style.get("newick", 0) + style.get("paren", 0) >= style.get("json", 0):
                        corpus.append(self._gen_newick(self._rng.randrange(3, 12)))
                    if style.get("json", 0) > 0:
                        corpus.append(self._gen_json_dup())
                    if style.get("cmd", 0) > 0:
                        corpus.append(self._gen_cmd_script(cmd_add))
                    if self._binary_mode:
                        corpus.append(self._gen_binary_guess())
                    if len(corpus) > 300:
                        corpus = corpus[-300:]

                parent = corpus[self._rng.randrange(0, len(corpus))]
                child = self._mutate(parent)
                if len(child) > 8192:
                    child = child[:8192]
                h = hash(child[:64] + bytes([len(child) & 0xFF]))
                if h in seen:
                    continue
                seen.add(h)
                if len(seen) > 6000:
                    seen = set(list(seen)[-2000:])

                rc, out, err = self._run(child)
                if self._is_target_crash(rc, err):
                    best_crash = child
                    break

                if rc != 124:
                    key = (rc << 24) ^ (hash(err[:120]) & 0xFFFFFF)
                    if key not in seen and len(child) <= 4096:
                        corpus.append(child)
                        if len(corpus) > 400:
                            corpus = corpus[-400:]

            if best_crash:
                minimized = self._ddmin(best_crash, test_crash, max_time=10.0)
                return minimized

            # Last resort: return a multi-pattern payload (not too large)
            fallback = (
                b"(a,b,c,d,e,f,g,h,i,j);\n"
                b'{"a":1,"a":2}\n'
                + self._gen_cmd_script(cmd_add)
                + b"<a><b></b><b></b><b></b><b></b></a>\n"
            )
            if len(fallback) < 60:
                fallback = (fallback * (60 // max(1, len(fallback)) + 1))[:60]
            return fallback[:512]