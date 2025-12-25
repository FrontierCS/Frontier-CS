import os
import re
import io
import sys
import tarfile
import time
import shutil
import struct
import tempfile
import hashlib
import random
import subprocess
from typing import List, Tuple, Optional, Callable, Dict, Set


class Solution:
    def solve(self, src_path: str) -> bytes:
        deadline = time.time() + 95.0

        def now() -> float:
            return time.time()

        def run_cmd(cmd: List[str], cwd: str, env: Dict[str, str], timeout: float) -> Tuple[int, bytes, bytes]:
            try:
                p = subprocess.run(
                    cmd,
                    cwd=cwd,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
                return p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired as e:
                out = e.stdout if e.stdout is not None else b""
                err = e.stderr if e.stderr is not None else b""
                return 124, out, err
            except Exception as e:
                return 127, b"", (str(e).encode("utf-8", "ignore"))

        def safe_read(path: str, max_bytes: int = 2_000_000) -> bytes:
            try:
                with open(path, "rb") as f:
                    return f.read(max_bytes)
            except Exception:
                return b""

        def extract_tar(tar_path: str, dst_dir: str) -> str:
            try:
                with tarfile.open(tar_path, "r:*") as tf:
                    tf.extractall(dst_dir)
            except Exception:
                return dst_dir
            try:
                entries = [os.path.join(dst_dir, x) for x in os.listdir(dst_dir)]
                dirs = [x for x in entries if os.path.isdir(x)]
                files = [x for x in entries if os.path.isfile(x)]
                if len(dirs) == 1 and not files:
                    return dirs[0]
            except Exception:
                pass
            return dst_dir

        def is_elf_executable(path: str) -> bool:
            try:
                st = os.stat(path)
                if not (st.st_mode & 0o111):
                    return False
                if st.st_size < 4096:
                    return False
                with open(path, "rb") as f:
                    hdr = f.read(4)
                return hdr == b"\x7fELF"
            except Exception:
                return False

        def find_source_files(root: str) -> List[str]:
            exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"}
            out = []
            for dp, dn, fn in os.walk(root):
                if "/.git/" in dp.replace("\\", "/"):
                    continue
                for name in fn:
                    _, ext = os.path.splitext(name)
                    if ext.lower() in exts:
                        out.append(os.path.join(dp, name))
            return out

        def find_dict_files(root: str) -> List[str]:
            out = []
            for dp, dn, fn in os.walk(root):
                if "/.git/" in dp.replace("\\", "/"):
                    continue
                for name in fn:
                    if name.endswith(".dict"):
                        out.append(os.path.join(dp, name))
            return out

        def extract_tokens_from_dict(path: str) -> List[bytes]:
            data = safe_read(path, 500_000)
            if not data:
                return []
            toks = []
            for m in re.finditer(rb'"([^"\r\n]{1,64})"', data):
                t = m.group(1)
                if t:
                    toks.append(t)
            for m in re.finditer(rb"=[ \t]*([^ \t\r\n]{1,64})", data):
                t = m.group(1)
                if t and b"\x00" not in t:
                    toks.append(t.strip())
            return toks

        def extract_string_literals(text_bytes: bytes) -> List[str]:
            try:
                s = text_bytes.decode("utf-8", "ignore")
            except Exception:
                return []
            strings = []
            for m in re.finditer(r'"((?:\\.|[^"\\]){1,128})"', s):
                lit = m.group(1)
                if not lit:
                    continue
                try:
                    decoded = bytes(lit, "utf-8").decode("unicode_escape", "ignore")
                except Exception:
                    decoded = lit
                if "\x00" in decoded:
                    continue
                strings.append(decoded)
            return strings

        def extract_magic_prefixes(text_bytes: bytes) -> List[bytes]:
            try:
                s = text_bytes.decode("utf-8", "ignore")
            except Exception:
                return []
            out = []
            patterns = [
                r"(?:memcmp|strncmp)\s*\([^,]+,\s*\"([^\"]{1,16})\"",
                r"(?:memcmp|strncmp)\s*\(\s*\"([^\"]{1,16})\"",
            ]
            for pat in patterns:
                for m in re.finditer(pat, s):
                    lit = m.group(1)
                    if not lit:
                        continue
                    try:
                        decoded = bytes(lit, "utf-8").decode("unicode_escape", "ignore")
                    except Exception:
                        decoded = lit
                    if decoded and all(32 <= ord(c) <= 126 for c in decoded):
                        out.append(decoded.encode("ascii", "ignore"))
            uniq = []
            seen = set()
            for x in out:
                if x not in seen and 1 <= len(x) <= 16:
                    seen.add(x)
                    uniq.append(x)
            return uniq

        def find_corpus_files(root: str) -> List[str]:
            candidates = []
            corpus_dir_names = {"corpus", "seed", "seeds", "inputs", "samples", "sample", "testcases", "examples", "example", "in"}
            for dp, dn, fn in os.walk(root):
                if "/.git/" in dp.replace("\\", "/"):
                    continue
                base = os.path.basename(dp).lower()
                if base in corpus_dir_names:
                    for name in fn:
                        p = os.path.join(dp, name)
                        try:
                            st = os.stat(p)
                        except Exception:
                            continue
                        if st.st_size <= 4096 and st.st_size > 0 and os.path.isfile(p):
                            candidates.append(p)
            candidates.sort(key=lambda p: (os.path.getsize(p), p))
            return candidates[:200]

        def rank_executables(exes: List[str]) -> List[str]:
            kws = ["poc", "target", "fuzz", "fuzzer", "main", "test", "demo", "run", "harness"]
            def score(p: str) -> Tuple[int, int, int, str]:
                bn = os.path.basename(p).lower()
                s = 0
                for i, kw in enumerate(kws):
                    if kw in bn:
                        s += 10 - min(i, 9)
                if bn.endswith(".so") or bn.endswith(".a"):
                    s -= 100
                try:
                    sz = os.path.getsize(p)
                except Exception:
                    sz = 0
                return (-s, sz, len(bn), p)
            return [p for p in sorted(exes, key=score)]

        def detect_crash(rc: int, stderr: bytes, stdout: bytes) -> bool:
            if rc == 0:
                return False
            hay = (stderr + b"\n" + stdout)[:200_000].lower()
            crash_markers = [
                b"addresssanitizer",
                b"asan:",
                b"heap-use-after-free",
                b"use-after-free",
                b"double-free",
                b"double free",
                b"free():",
                b"invalid pointer",
                b"malloc():",
                b"corruption",
                b"sanitizer",
                b"runtime error:",
                b"glibc detected",
                b"aborted",
                b"segmentation fault",
            ]
            if rc < 0:
                return True
            for m in crash_markers:
                if m in hay:
                    return True
            return False

        def try_run_exe(exe: str, inp: bytes, timeout: float = 1.25) -> Tuple[bool, int, bytes, bytes]:
            env = os.environ.copy()
            env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0:allocator_may_return_null=1:handle_segv=1")
            env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")
            try:
                p = subprocess.run(
                    [exe],
                    input=inp,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env=env,
                )
                crashed = detect_crash(p.returncode, p.stderr, p.stdout)
                if crashed:
                    return True, p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired as e:
                pass
            except Exception:
                pass

            # try with temp file arg
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(inp)
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
                    crashed = detect_crash(p.returncode, p.stderr, p.stdout)
                    return crashed, p.returncode, p.stdout, p.stderr
                finally:
                    try:
                        os.unlink(tmpname)
                    except Exception:
                        pass
            except Exception:
                return False, 127, b"", b""
            return False, 0, b"", b""

        def collect_executables(root: str) -> List[str]:
            exes = []
            for dp, dn, fn in os.walk(root):
                if "/.git/" in dp.replace("\\", "/"):
                    continue
                for name in fn:
                    p = os.path.join(dp, name)
                    if is_elf_executable(p):
                        exes.append(p)
            return exes

        def attempt_build(root: str) -> None:
            if now() > deadline:
                return
            env = os.environ.copy()
            sanitize = "-fsanitize=address -fno-omit-frame-pointer"
            env["CFLAGS"] = (env.get("CFLAGS", "") + " " + sanitize + " -O1 -g").strip()
            env["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " " + sanitize + " -O1 -g").strip()
            env["LDFLAGS"] = (env.get("LDFLAGS", "") + " " + sanitize).strip()
            env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0:allocator_may_return_null=1")
            env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")

            build_sh = os.path.join(root, "build.sh")
            if os.path.isfile(build_sh):
                run_cmd(["bash", "build.sh"], cwd=root, env=env, timeout=max(1.0, min(45.0, deadline - now())))
                return

            cmakelists = os.path.join(root, "CMakeLists.txt")
            makefile = os.path.join(root, "Makefile")
            if os.path.isfile(cmakelists):
                bdir = os.path.join(root, "build")
                os.makedirs(bdir, exist_ok=True)
                gen = []
                if shutil.which("ninja"):
                    gen = ["-G", "Ninja"]
                cmake_timeout = max(1.0, min(45.0, deadline - now()))
                run_cmd(
                    ["cmake"] + gen + [
                        "-S", ".",
                        "-B", "build",
                        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                        f"-DCMAKE_C_FLAGS={env['CFLAGS']}",
                        f"-DCMAKE_CXX_FLAGS={env['CXXFLAGS']}",
                        f"-DCMAKE_EXE_LINKER_FLAGS={env['LDFLAGS']}",
                    ],
                    cwd=root,
                    env=env,
                    timeout=cmake_timeout,
                )
                build_timeout = max(1.0, min(55.0, deadline - now()))
                run_cmd(["cmake", "--build", "build", "-j8"], cwd=root, env=env, timeout=build_timeout)
                return

            if os.path.isfile(makefile):
                make_timeout = max(1.0, min(55.0, deadline - now()))
                run_cmd(["make", "-j8"], cwd=root, env=env, timeout=make_timeout)
                return

        def seed_rng_from_tar(path: str) -> random.Random:
            h = hashlib.sha256()
            try:
                with open(path, "rb") as f:
                    h.update(f.read(1_000_000))
            except Exception:
                h.update(path.encode("utf-8", "ignore"))
            seed = int.from_bytes(h.digest()[:8], "little", signed=False)
            return random.Random(seed)

        def generate_common_format_candidates() -> List[bytes]:
            c = []
            c.append(b'{"a":1,"a":2}\n')
            c.append(b'{"a":[1,2,3,4],"a":[5]}\n')
            c.append(b"a: 1\na: 2\n")
            c.append(b"<a><b></b><b></b></a>\n")
            c.append(b"a=a\na=a\n")
            c.append(b"a=1&a=2\n")
            c.append(b"[a]\nx=1\nx=2\n")
            c.append(b"add 0\nadd 0\n")
            c.append(b"add 0 0\nadd 0 0\n")
            c.append(b"add 1 2\nadd 1 2\n")
            c.append(b"ADD 1 2\nADD 1 2\n")
            c.append(b"insert 1 2\ninsert 1 2\n")
            c.append(b"push 1\npush 1\n")
            c.append(b"append 1\nappend 1\n")
            c.append(b"node 0\nadd 0 0\nadd 0 0\n")
            c.append(b"add -1\nadd -1\n")
            c.append(b"add 2147483647\nadd 2147483647\n")
            c.append(b"\x00" * 60)
            c.append(b"A" * 60)
            c.append(bytes(range(60)))
            c.append((b"\xff" * 60))
            return c

        def generate_text_script_candidates(tokens: List[bytes]) -> List[bytes]:
            toks = [t for t in tokens if t and len(t) <= 16]
            tokset = set(t.lower() for t in toks)
            preferred = []
            for kw in [b"add", b"insert", b"append", b"push", b"new", b"node", b"del", b"delete", b"remove", b"set", b"put"]:
                if kw in tokset:
                    preferred.append(kw.decode("ascii", "ignore"))
            if not preferred:
                preferred = ["add", "insert", "append", "push", "set", "put", "node"]
            scripts = []
            nums = ["0", "1", "2", "3", "4", "-1", "2147483647", "4294967295"]
            seps = ["\n", "\r\n", ";", "\n\n"]
            for cmd in preferred[:6]:
                for sep in seps:
                    scripts.append(f"{cmd} 0{sep}{cmd} 0{sep}".encode("ascii", "ignore"))
                    scripts.append(f"{cmd} 0 0{sep}{cmd} 0 0{sep}".encode("ascii", "ignore"))
                    scripts.append(f"{cmd} 1 2{sep}{cmd} 1 2{sep}".encode("ascii", "ignore"))
                    scripts.append(f"{cmd} 0 1{sep}{cmd} 0 2{sep}{cmd} 0 3{sep}".encode("ascii", "ignore"))
                    scripts.append(f"{cmd} -1{sep}{cmd} -1{sep}".encode("ascii", "ignore"))
                    scripts.append(f"{cmd} 2147483647{sep}{cmd} 2147483647{sep}".encode("ascii", "ignore"))

            if b"delete" in tokset or b"remove" in tokset or b"del" in tokset:
                delcmd = "delete" if b"delete" in tokset else ("remove" if b"remove" in tokset else "del")
                scripts.append(f"add 1{seps[0]}{delcmd} 1{seps[0]}add 1{seps[0]}".encode("ascii", "ignore"))
                scripts.append(f"add 1 2{seps[0]}{delcmd} 2{seps[0]}add 1 2{seps[0]}".encode("ascii", "ignore"))

            uniq = []
            seen = set()
            for s in scripts:
                if s not in seen and 1 <= len(s) <= 512:
                    seen.add(s)
                    uniq.append(s)
            uniq.sort(key=len)
            return uniq

        def generate_binary_candidates(rng: random.Random, magic_prefixes: List[bytes], tokens: List[bytes]) -> List[bytes]:
            out = []
            for l in [1, 2, 3, 4, 8, 12, 16, 24, 32, 48, 60, 64, 80, 96, 128]:
                out.append(b"\x00" * l)
                out.append(b"\xff" * l)
                out.append(bytes([0x41]) * l)
                out.append(bytes(range(l)) if l <= 256 else bytes(range(256)) + b"\x00" * (l - 256))
                out.append(bytes([rng.randrange(256) for _ in range(l)]))
            for mp in magic_prefixes[:8]:
                for l in [len(mp), 16, 32, 60, 64]:
                    if l < len(mp):
                        continue
                    pad = bytes([0x00]) * (l - len(mp))
                    out.append(mp + pad)
                    out.append(mp + bytes([rng.randrange(256) for _ in range(l - len(mp))]))
            # embed tokens
            text_toks = [t for t in tokens if t and len(t) <= 16 and all(32 <= b <= 126 for b in t)]
            for t in text_toks[:40]:
                for l in [32, 60, 64, 80]:
                    base = t + b"\n" + t + b"\n"
                    if len(base) >= l:
                        out.append(base[:l])
                    else:
                        out.append(base + bytes([0]) * (l - len(base)))
            uniq = []
            seen = set()
            for b in out:
                if b not in seen and 1 <= len(b) <= 512:
                    seen.add(b)
                    uniq.append(b)
            uniq.sort(key=len)
            return uniq

        def mutate(rng: random.Random, data: bytes, tokens: List[bytes]) -> bytes:
            if not data:
                data = b"\x00"
            b = bytearray(data)
            ops = rng.randrange(8)
            if ops == 0 and len(b) > 1:
                # delete a chunk
                start = rng.randrange(len(b))
                end = min(len(b), start + 1 + rng.randrange(min(16, len(b) - start)))
                del b[start:end]
            elif ops == 1:
                # insert random bytes
                pos = rng.randrange(len(b) + 1)
                ln = 1 + rng.randrange(16)
                ins = bytes([rng.randrange(256) for _ in range(ln)])
                b[pos:pos] = ins
            elif ops == 2:
                # flip some bits
                for _ in range(1 + rng.randrange(8)):
                    i = rng.randrange(len(b))
                    b[i] ^= 1 << rng.randrange(8)
            elif ops == 3:
                # overwrite a chunk with random
                if len(b) > 0:
                    start = rng.randrange(len(b))
                    ln = 1 + rng.randrange(min(16, len(b) - start))
                    for i in range(start, start + ln):
                        b[i] = rng.randrange(256)
            elif ops == 4:
                # duplicate a chunk
                if len(b) > 1:
                    start = rng.randrange(len(b))
                    end = min(len(b), start + 1 + rng.randrange(min(16, len(b) - start)))
                    pos = rng.randrange(len(b) + 1)
                    b[pos:pos] = b[start:end]
            elif ops == 5:
                # append small integer pack
                v = rng.randrange(0, 1 << 32)
                b += struct.pack("<I", v)
            elif ops == 6:
                # splice in a token
                tt = [t for t in tokens if t and len(t) <= 32 and b"\x00" not in t]
                if tt:
                    t = rng.choice(tt)
                    pos = rng.randrange(len(b) + 1)
                    if rng.randrange(2) == 0:
                        b[pos:pos] = t + b"\n"
                    else:
                        b[pos:pos] = t
            else:
                # truncate
                if len(b) > 1:
                    new_len = 1 + rng.randrange(min(len(b), 96))
                    b = b[:new_len]
            if len(b) > 512:
                b = b[:512]
            if len(b) == 0:
                b = bytearray(b"\x00")
            return bytes(b)

        def ddmin(data: bytes, test: Callable[[bytes], bool], until: float) -> bytes:
            if not data or len(data) <= 1:
                return data
            if not test(data):
                return data
            n = 2
            cur = data
            while len(cur) >= 2 and now() < until:
                length = len(cur)
                chunk = (length + n - 1) // n
                reduced = False
                for i in range(n):
                    if now() >= until:
                        break
                    start = i * chunk
                    end = min(length, start + chunk)
                    if start >= end:
                        continue
                    cand = cur[:start] + cur[end:]
                    if not cand:
                        continue
                    if test(cand):
                        cur = cand
                        n = max(2, n - 1)
                        reduced = True
                        break
                if not reduced:
                    if n >= len(cur):
                        break
                    n = min(len(cur), n * 2)
            return cur

        with tempfile.TemporaryDirectory() as td:
            root = extract_tar(src_path, td)

            rng = seed_rng_from_tar(src_path)

            # Pre-scan sources for tokens/magic and corpus
            src_files = find_source_files(root)
            dict_files = find_dict_files(root)
            corpus_files = find_corpus_files(root)

            tokens: List[bytes] = []
            for df in dict_files[:20]:
                if now() > deadline:
                    break
                tokens.extend(extract_tokens_from_dict(df))

            magic_prefixes: List[bytes] = []
            if src_files:
                # sample subset of files to keep it fast
                sample_files = src_files[:]
                rng.shuffle(sample_files)
                sample_files = sample_files[:60]
                for sp in sample_files:
                    if now() > deadline:
                        break
                    tb = safe_read(sp, 400_000)
                    if not tb:
                        continue
                    magic_prefixes.extend(extract_magic_prefixes(tb))
                    lits = extract_string_literals(tb)
                    for lit in lits:
                        if 2 <= len(lit) <= 32 and all(32 <= ord(c) <= 126 for c in lit):
                            bl = lit.encode("utf-8", "ignore")
                            if b"\x00" not in bl:
                                tokens.append(bl)

            # Normalize tokens
            norm_tokens = []
            seen_tok = set()
            for t in tokens:
                if not t:
                    continue
                if len(t) > 64:
                    continue
                tt = t.strip()
                if not tt:
                    continue
                if tt in seen_tok:
                    continue
                seen_tok.add(tt)
                norm_tokens.append(tt)
            tokens = norm_tokens

            # Build if needed
            exes = collect_executables(root)
            if not exes and now() < deadline:
                attempt_build(root)
                exes = collect_executables(root)

            if not exes:
                # As a last resort, return some likely-text PoC around ground-truth length
                return (b"add 1 2\nadd 1 2\n" + b"A" * 42)[:60]

            exes = rank_executables(exes)
            exes = exes[:8]

            # Candidate pool
            candidates: List[bytes] = []
            candidates.extend(generate_common_format_candidates())

            # corpus seeds
            for cf in corpus_files[:80]:
                if now() > deadline:
                    break
                b = safe_read(cf, 4096)
                if 0 < len(b) <= 512:
                    candidates.append(b)
                    if len(b) <= 256:
                        candidates.append(b + b)
                    if b.count(b"\n") >= 1:
                        lines = b.splitlines(keepends=True)
                        if lines:
                            candidates.append(b"".join(lines[: min(4, len(lines))] * 2)[:512])

            # text scripts based on tokens
            candidates.extend(generate_text_script_candidates(tokens))

            # binary candidates
            candidates.extend(generate_binary_candidates(rng, magic_prefixes, tokens))

            # de-dup + sort by length
            uniq: List[bytes] = []
            seen = set()
            for c in candidates:
                if not c:
                    continue
                if len(c) > 512:
                    c = c[:512]
                if c in seen:
                    continue
                seen.add(c)
                uniq.append(c)
            uniq.sort(key=len)
            candidates = uniq

            # Test function for current best executable(s)
            crash_input: Optional[bytes] = None
            crash_exe: Optional[str] = None

            def test_input(inp: bytes) -> bool:
                nonlocal crash_input, crash_exe
                for exe in exes:
                    crashed, rc, out, err = try_run_exe(exe, inp, timeout=1.25)
                    if crashed:
                        crash_input = inp
                        crash_exe = exe
                        return True
                return False

            # First pass: deterministic candidates
            for c in candidates:
                if now() > deadline:
                    break
                if test_input(c):
                    break

            # Fuzz if not found
            if crash_input is None and now() < deadline:
                # start with some seeds
                seed_pool = candidates[:80] if candidates else [b"\x00"]
                if not seed_pool:
                    seed_pool = [b"\x00" * 60]
                max_iters = 4000
                for i in range(max_iters):
                    if now() > deadline:
                        break
                    base = seed_pool[rng.randrange(len(seed_pool))]
                    m = mutate(rng, base, tokens)
                    if test_input(m):
                        break
                    # occasionally mutate previous mutated
                    if rng.randrange(8) == 0:
                        m2 = mutate(rng, m, tokens)
                        if test_input(m2):
                            break

            if crash_input is None:
                # fallback: try a slightly larger set with repeated 'add'
                fallback = (b"add 0 0\n" * 10)[:120]
                if test_input(fallback):
                    pass
                else:
                    return (b"add 0 0\nadd 0 0\n" + b"\x00" * 60)[:60]

            # Minimize on the crashing executable only (faster / more stable)
            chosen_exe = crash_exe if crash_exe is not None else exes[0]
            base_input = crash_input if crash_input is not None else b"\x00" * 60

            def test_one_exe(inp: bytes) -> bool:
                crashed, rc, out, err = try_run_exe(chosen_exe, inp, timeout=1.25)
                return crashed

            # Only minimize if time allows and input isn't already small
            min_deadline = min(deadline, now() + 12.0)
            if len(base_input) > 80 and now() < min_deadline:
                base_input = ddmin(base_input, test_one_exe, until=min_deadline)

            # final clamp to keep it reasonable
            if len(base_input) > 512:
                base_input = base_input[:512]
            if not base_input:
                base_input = b"\x00"

            return base_input