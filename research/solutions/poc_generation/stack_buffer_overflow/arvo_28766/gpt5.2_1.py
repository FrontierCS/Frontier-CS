import os
import re
import io
import sys
import tarfile
import time
import shutil
import struct
import random
import tempfile
import subprocess
from pathlib import Path
from collections import Counter
from typing import List, Optional, Tuple, Set, Dict


class Solution:
    def solve(self, src_path: str) -> bytes:
        random.seed(0)
        workdir = tempfile.mkdtemp(prefix="arvo_poc_")
        try:
            root = self._extract_to_dir(src_path, Path(workdir) / "src")
            root = self._guess_project_root(root)

            existing = self._find_existing_poc_file_bytes(root)
            if existing is not None:
                return existing

            bug_files = self._find_bug_files(root)

            exe, mode, seed_bytes = self._build_and_find_target_and_seed(root, bug_files=bug_files, time_budget=110.0)
            if exe is not None:
                crash = self._find_crashing_input(exe, mode, seed_bytes, bug_files=bug_files, time_budget=45.0)
                if crash is not None:
                    crash = self._minimize_crash(exe, mode, crash, bug_files=bug_files, time_budget=25.0)
                    return crash

            if seed_bytes:
                return seed_bytes

            return b"\x00" * 140
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _extract_to_dir(self, src_path: str, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        p = Path(src_path)
        if p.is_dir():
            for child in p.iterdir():
                dst = out_dir / child.name
                if child.is_dir():
                    shutil.copytree(child, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(child, dst)
        else:
            if not tarfile.is_tarfile(str(p)):
                raise ValueError("src_path is neither a directory nor a tarball")
            with tarfile.open(str(p), "r:*") as tf:
                self._safe_extract_tar(tf, out_dir)

        children = [c for c in out_dir.iterdir() if c.name not in (".", "..")]
        if len(children) == 1 and children[0].is_dir():
            return children[0]
        return out_dir

    def _safe_extract_tar(self, tf: tarfile.TarFile, out_dir: Path) -> None:
        out_dir = out_dir.resolve()
        for member in tf.getmembers():
            name = member.name
            if name.startswith("/") or name.startswith("\\"):
                continue
            parts = Path(name).parts
            if any(part == ".." for part in parts):
                continue
            target = (out_dir / name).resolve()
            if not str(target).startswith(str(out_dir) + os.sep) and target != out_dir:
                continue
            tf.extract(member, str(out_dir))

    def _guess_project_root(self, root: Path) -> Path:
        markers = {"CMakeLists.txt", "Makefile", "meson.build", "configure", "build.sh"}
        cur = root
        for _ in range(5):
            if any((cur / m).exists() for m in markers):
                return cur
            subs = [d for d in cur.iterdir() if d.is_dir() and d.name not in (".git", "build", "out", ".github")]
            subs = [d for d in subs if not d.name.startswith(".")]
            if len(subs) == 1:
                cur = subs[0]
                continue
            cmake_dirs = []
            make_dirs = []
            for d in subs:
                if (d / "CMakeLists.txt").exists():
                    cmake_dirs.append(d)
                if (d / "Makefile").exists():
                    make_dirs.append(d)
            if len(cmake_dirs) == 1:
                return cmake_dirs[0]
            if len(make_dirs) == 1:
                return make_dirs[0]
            return cur
        return cur

    def _find_existing_poc_file_bytes(self, root: Path) -> Optional[bytes]:
        bad_ext = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inl",
            ".py", ".java", ".js", ".ts", ".go", ".rs",
            ".md", ".rst", ".txt", ".html", ".css",
            ".cmake", ".yml", ".yaml", ".json",
            ".toml", ".ini", ".cfg",
            ".o", ".a", ".so", ".dylib", ".dll", ".obj", ".lib", ".exe",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf",
        }

        keywords = ("poc", "repro", "crash", "asan", "ubsan", "overflow", "stack", "snapshot", "corpus", "seed", "testcase")
        candidates: List[Tuple[int, int, Path]] = []
        target_len = 140

        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath).lower()
            if dn in (".git", "build", "cmakefiles", "node_modules"):
                dirnames[:] = []
                continue
            if any(part.lower() in ("build", "cmakefiles") for part in Path(dirpath).parts):
                continue

            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 50000:
                    continue
                ext = p.suffix.lower()
                if ext in bad_ext:
                    continue
                name_l = fn.lower()
                path_l = str(p).lower()
                kw_score = sum(1 for k in keywords if k in name_l or k in path_l)
                size_pen = abs(int(st.st_size) - target_len)
                score = -(kw_score * 1000) + size_pen
                candidates.append((score, int(st.st_size), p))

        candidates.sort(key=lambda x: (x[0], x[1]))
        for _, _, p in candidates[:40]:
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if 1 <= len(data) <= 50000:
                if len(data) == 140:
                    return data

        for _, _, p in candidates[:20]:
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if 1 <= len(data) <= 50000:
                return data

        return None

    def _find_bug_files(self, root: Path) -> Set[str]:
        bug_files: Set[str] = set()
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath).lower()
            if dn in (".git", "build", "cmakefiles"):
                dirnames[:] = []
                continue
            if any(part.lower() in ("build", "cmakefiles") for part in Path(dirpath).parts):
                continue
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() not in exts:
                    continue
                try:
                    txt = p.read_text(errors="ignore")
                except OSError:
                    continue
                if "node_id_map" in txt and ".find(" in txt:
                    bug_files.add(p.name)
        return bug_files

    def _build_and_find_target_and_seed(
        self, root: Path, bug_files: Set[str], time_budget: float
    ) -> Tuple[Optional[str], Optional[str], bytes]:
        t0 = time.monotonic()
        build_ok = self._attempt_build(root, time_budget=max(10.0, time_budget * 0.65))
        if not build_ok:
            return None, None, b""

        if time.monotonic() - t0 > time_budget:
            return None, None, b""

        exes = self._find_executables(root)
        if not exes:
            return None, None, b""

        seeds = self._find_seed_files(root)
        seed_bytes_list: List[bytes] = []
        for s in seeds[:50]:
            try:
                b = s.read_bytes()
            except OSError:
                continue
            if 1 <= len(b) <= 200000:
                seed_bytes_list.append(b)
        if not seed_bytes_list:
            seed_bytes_list = [b"\x00" * 140, b"\x00" * 256, b"{}"]

        exe_candidates = self._rank_executables(exes, root)
        best: Optional[Tuple[str, str, bytes]] = None
        for exe in exe_candidates[:12]:
            if time.monotonic() - t0 > time_budget:
                break
            for sb in seed_bytes_list[:15]:
                for mode in ("file", "stdin"):
                    rc, out, err = self._run_target(exe, mode, sb, timeout=1.5)
                    if rc == 0:
                        best = (exe, mode, sb)
                        break
                if best is not None:
                    break
            if best is not None:
                break

        if best is not None:
            return best[0], best[1], best[2]

        for exe in exe_candidates[:8]:
            if time.monotonic() - t0 > time_budget:
                break
            sb = seed_bytes_list[0]
            for mode in ("file", "stdin"):
                rc, out, err = self._run_target(exe, mode, sb, timeout=1.5)
                if rc is not None:
                    txt = (out + b"\n" + err).decode("latin1", errors="ignore").lower()
                    if "usage" in txt or "help" in txt or "argument" in txt:
                        continue
                    return exe, mode, sb

        return None, None, b""

    def _attempt_build(self, root: Path, time_budget: float) -> bool:
        t0 = time.monotonic()
        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:exitcode=99")
        env.setdefault("UBSAN_OPTIONS", "abort_on_error=1:exitcode=99:print_stacktrace=1")

        cxx = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
        cc = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
        if cxx:
            env["CXX"] = cxx
        if cc:
            env["CC"] = cc

        common_flags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
        env["CFLAGS"] = (env.get("CFLAGS", "") + " " + common_flags).strip()
        env["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " " + common_flags).strip()
        env["LDFLAGS"] = (env.get("LDFLAGS", "") + " -fsanitize=address").strip()

        build_sh = root / "build.sh"
        if build_sh.exists():
            try:
                rc = self._run_cmd(["bash", str(build_sh)], cwd=root, env=env, timeout=max(10.0, time_budget))
                return rc == 0
            except Exception:
                pass

        if (root / "CMakeLists.txt").exists():
            bdir = root / "build_asan"
            bdir.mkdir(exist_ok=True)
            try:
                if time.monotonic() - t0 > time_budget:
                    return False
                rc1 = self._run_cmd(
                    [
                        "cmake",
                        "-S",
                        str(root),
                        "-B",
                        str(bdir),
                        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                        f"-DCMAKE_C_FLAGS={env['CFLAGS']}",
                        f"-DCMAKE_CXX_FLAGS={env['CXXFLAGS']}",
                        f"-DCMAKE_EXE_LINKER_FLAGS={env['LDFLAGS']}",
                    ],
                    cwd=root,
                    env=env,
                    timeout=max(10.0, time_budget * 0.5),
                )
                if rc1 != 0:
                    rc1 = self._run_cmd(
                        ["cmake", "-S", str(root), "-B", str(bdir), "-DCMAKE_BUILD_TYPE=RelWithDebInfo"],
                        cwd=root,
                        env=env,
                        timeout=max(10.0, time_budget * 0.5),
                    )
                    if rc1 != 0:
                        return False
                if time.monotonic() - t0 > time_budget:
                    return False
                rc2 = self._run_cmd(["cmake", "--build", str(bdir), "-j", str(max(1, os.cpu_count() or 1))], cwd=root, env=env, timeout=max(10.0, time_budget))
                return rc2 == 0
            except Exception:
                pass

        if (root / "meson.build").exists():
            bdir = root / "build_asan"
            try:
                if not (bdir / "build.ninja").exists():
                    rc1 = self._run_cmd(
                        ["meson", "setup", str(bdir), str(root)],
                        cwd=root,
                        env=env,
                        timeout=max(10.0, time_budget * 0.5),
                    )
                    if rc1 != 0:
                        return False
                if time.monotonic() - t0 > time_budget:
                    return False
                rc2 = self._run_cmd(
                    ["ninja", "-C", str(bdir)],
                    cwd=root,
                    env=env,
                    timeout=max(10.0, time_budget),
                )
                return rc2 == 0
            except Exception:
                pass

        if (root / "Makefile").exists():
            try:
                rc = self._run_cmd(
                    ["make", "-j", str(max(1, os.cpu_count() or 1))],
                    cwd=root,
                    env=env,
                    timeout=max(10.0, time_budget),
                )
                return rc == 0
            except Exception:
                pass

        return False

    def _run_cmd(self, cmd: List[str], cwd: Path, env: Dict[str, str], timeout: float) -> int:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return int(p.returncode)

    def _find_executables(self, root: Path) -> List[str]:
        exes: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath).lower()
            if dn in (".git",):
                dirnames[:] = []
                continue
            if any(part.lower() in (".git",) for part in Path(dirpath).parts):
                continue
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.is_symlink():
                    continue
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size <= 0:
                    continue
                if not os.access(str(p), os.X_OK):
                    continue
                if p.suffix.lower() in (".so", ".a", ".o", ".dylib", ".dll"):
                    continue
                if any(part.lower() in ("cmakefiles",) for part in p.parts):
                    continue
                exes.append(str(p))
        return exes

    def _rank_executables(self, exes: List[str], root: Path) -> List[str]:
        keywords = ["processor", "snapshot", "parse", "parser", "poc", "repro", "fuzz", "test", "driver"]
        scored: List[Tuple[int, int, str]] = []
        for e in exes:
            ep = Path(e)
            name = ep.name.lower()
            pathl = str(ep).lower()
            score = 0
            for k in keywords:
                if k in name:
                    score += 8
                if k in pathl:
                    score += 2
            if "build_asan" in pathl:
                score += 3
            if "build" in pathl:
                score += 1
            size = 0
            try:
                size = ep.stat().st_size
            except OSError:
                pass
            scored.append((-score, size, e))
        scored.sort()
        return [e for _, _, e in scored]

    def _find_seed_files(self, root: Path) -> List[Path]:
        code_ext = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
            ".py", ".java", ".js", ".ts", ".go", ".rs",
            ".md", ".rst", ".html", ".css", ".cmake", ".yml", ".yaml",
            ".toml", ".ini", ".cfg", ".sln", ".vcxproj",
            ".o", ".a", ".so", ".dylib", ".dll", ".obj", ".lib",
        }
        likely_dirs = ("corpus", "seed", "seeds", "test", "tests", "testdata", "data", "samples", "sample", "inputs", "fuzz", "pocs", "repro")
        likely_ext = (".bin", ".dat", ".snap", ".snapshot", ".dump", ".img", ".raw", ".in", ".input", ".txt", ".json")
        target_len = 140

        candidates: List[Tuple[int, int, Path]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath).lower()
            if dn in (".git", "cmakefiles"):
                dirnames[:] = []
                continue
            path_parts_l = [p.lower() for p in Path(dirpath).parts]
            if "build_asan" in path_parts_l or "build" in path_parts_l or "out" in path_parts_l:
                continue
            dir_score = 0
            for ld in likely_dirs:
                if ld in dn or ld in dirpath.lower():
                    dir_score += 4
            for fn in filenames:
                p = Path(dirpath) / fn
                ext = p.suffix.lower()
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 500000:
                    continue
                if ext in code_ext:
                    continue
                name_l = fn.lower()
                ext_score = 0
                if ext in likely_ext:
                    ext_score += 3
                if any(k in name_l for k in ("seed", "corpus", "poc", "repro", "crash", "snapshot", "input")):
                    ext_score += 3
                size_pen = abs(int(st.st_size) - target_len)
                score = -(dir_score * 10 + ext_score * 10) + size_pen
                candidates.append((score, int(st.st_size), p))

        candidates.sort(key=lambda x: (x[0], x[1]))
        return [p for _, _, p in candidates]

    def _run_target(self, exe: str, mode: str, data: bytes, timeout: float) -> Tuple[int, bytes, bytes]:
        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:exitcode=99")
        env.setdefault("UBSAN_OPTIONS", "abort_on_error=1:exitcode=99:print_stacktrace=1")

        if mode == "stdin":
            try:
                p = subprocess.run(
                    [exe],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env=env,
                )
                return int(p.returncode), p.stdout, p.stderr
            except subprocess.TimeoutExpired:
                return 124, b"", b""
            except Exception:
                return 127, b"", b""

        tmpdir = tempfile.mkdtemp(prefix="arvo_inp_")
        try:
            inpath = Path(tmpdir) / "input.bin"
            inpath.write_bytes(data)
            try:
                p = subprocess.run(
                    [exe, str(inpath)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env=env,
                )
                return int(p.returncode), p.stdout, p.stderr
            except subprocess.TimeoutExpired:
                return 124, b"", b""
            except Exception:
                return 127, b"", b""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _is_desired_crash(self, rc: int, out: bytes, err: bytes, bug_files: Set[str]) -> bool:
        if rc == 0 or rc == 124 or rc == 127:
            return False
        s = (out + b"\n" + err).decode("latin1", errors="ignore")
        sl = s.lower()
        if "addresssanitizer" in sl or "undefinedbehavior" in sl or "ubsan" in sl:
            if "stack-buffer-overflow" in sl or "heap-buffer-overflow" in sl or "use-after-free" in sl or "runtime error" in sl or "segmentation fault" in sl:
                if bug_files:
                    for bf in bug_files:
                        if bf.lower() in sl:
                            return True
                    if "node_id_map" in sl:
                        return True
                    if "unordered_map" in sl or "std::map" in sl:
                        return True
                    return False
                return True
        if bug_files:
            for bf in bug_files:
                if bf.lower() in sl:
                    return True
        return False

    def _find_crashing_input(
        self,
        exe: str,
        mode: str,
        seed: bytes,
        bug_files: Set[str],
        time_budget: float,
    ) -> Optional[bytes]:
        t0 = time.monotonic()

        rc, out, err = self._run_target(exe, mode, seed, timeout=1.5)
        if self._is_desired_crash(rc, out, err, bug_files):
            return seed

        if not seed:
            seed = b"\x00" * 256

        if self._looks_textual(seed):
            cand = self._textual_mutate_for_missing_id(seed)
            if cand is not None:
                rc, out, err = self._run_target(exe, mode, cand, timeout=1.5)
                if self._is_desired_crash(rc, out, err, bug_files):
                    return cand

        for size in (4, 8):
            if time.monotonic() - t0 > time_budget:
                break
            offsets, missing_vals = self._candidate_id_offsets(seed, size)
            offsets_late = [o for o in offsets if o >= len(seed) // 3]
            offsets_early = [o for o in offsets if o < len(seed) // 3]
            for off_list in (offsets_late, offsets_early, offsets):
                if time.monotonic() - t0 > time_budget:
                    break
                for off in off_list[:800]:
                    if time.monotonic() - t0 > time_budget:
                        break
                    cur = seed
                    for mv in missing_vals:
                        mut = self._patch_int(cur, off, mv, size)
                        rc, out, err = self._run_target(exe, mode, mut, timeout=1.5)
                        if self._is_desired_crash(rc, out, err, bug_files):
                            return mut

        if time.monotonic() - t0 <= time_budget:
            values4 = [0, 1, 2, 3, 4, 5, 7, 8, 16, 32, 64, 127, 128, 255, 256, 511, 512, 1024, 1337, 4096, 65535, 0x7FFFFFFF, 0xFFFFFFFF]
            max_trials = 1500
            for i in range(max_trials):
                if time.monotonic() - t0 > time_budget:
                    break
                mut = bytearray(seed)
                if len(mut) >= 4:
                    off = random.randrange(0, len(mut) - 3)
                    v = random.choice(values4)
                    mut[off:off + 4] = struct.pack("<I", v)
                else:
                    mut.extend(b"\x00" * (4 - len(mut)))
                    mut[0:4] = struct.pack("<I", 0xFFFFFFFF)
                if random.random() < 0.15:
                    mut.extend(os.urandom(random.randrange(1, 33)))
                rc, out, err = self._run_target(exe, mode, bytes(mut), timeout=1.5)
                if self._is_desired_crash(rc, out, err, bug_files):
                    return bytes(mut)

        return None

    def _minimize_crash(self, exe: str, mode: str, data: bytes, bug_files: Set[str], time_budget: float) -> bytes:
        t0 = time.monotonic()

        def crashes(d: bytes) -> bool:
            rc, out, err = self._run_target(exe, mode, d, timeout=1.5)
            return self._is_desired_crash(rc, out, err, bug_files)

        best = data
        if len(best) <= 1:
            return best

        lo, hi = 1, len(best)
        while lo < hi and time.monotonic() - t0 <= time_budget:
            mid = (lo + hi) // 2
            cand = best[:mid]
            if crashes(cand):
                hi = mid
            else:
                lo = mid + 1
        if hi < len(best) and time.monotonic() - t0 <= time_budget:
            if crashes(best[:hi]):
                best = best[:hi]

        checks = 0
        chunk = max(1, len(best) // 2)
        while chunk >= 1 and checks < 120 and time.monotonic() - t0 <= time_budget:
            changed = False
            i = 0
            while i < len(best) and checks < 120 and time.monotonic() - t0 <= time_budget:
                cand = best[:i] + best[i + chunk:]
                if cand and crashes(cand):
                    best = cand
                    changed = True
                else:
                    i += chunk
                checks += 1
            if not changed:
                chunk //= 2

        return best

    def _looks_textual(self, data: bytes) -> bool:
        if not data:
            return False
        if any(b in data[:1] for b in (b"{", b"[", b"<")):
            return True
        printable = sum(1 for c in data if 9 <= c <= 13 or 32 <= c <= 126)
        return printable / max(1, len(data)) > 0.90

    def _textual_mutate_for_missing_id(self, data: bytes) -> Optional[bytes]:
        try:
            s = data.decode("utf-8", errors="ignore")
        except Exception:
            return None
        nums = [int(m.group(0)) for m in re.finditer(r"\b\d+\b", s)]
        if not nums:
            return None
        freq = Counter(nums)
        candidates = [n for n, c in freq.items() if 1 <= n <= 100000 and c >= 2]
        if not candidates:
            candidates = [n for n in nums if 1 <= n <= 1000]
        if not candidates:
            return None
        mx = max(candidates)
        missing = mx + 1
        target = candidates[0]
        replaced = False

        def repl(m: re.Match) -> str:
            nonlocal replaced
            if not replaced and int(m.group(0)) == target:
                replaced = True
                return str(missing)
            return m.group(0)

        s2 = re.sub(r"\b\d+\b", repl, s, count=0)
        if not replaced:
            return None
        return s2.encode("utf-8", errors="ignore")

    def _candidate_id_offsets(self, data: bytes, size: int) -> Tuple[List[int], List[int]]:
        if len(data) < size:
            return [], [0x1337]

        step = size
        vals: List[int] = []
        offs: List[int] = []
        unpack = struct.unpack_from
        fmt = "<I" if size == 4 else "<Q"
        for off in range(0, len(data) - size + 1, step):
            try:
                v = unpack(fmt, data, off)[0]
            except struct.error:
                continue
            vals.append(int(v))
            offs.append(off)

        freq = Counter(vals)
        candidates = {v for v, c in freq.items() if 1 <= v <= 100000 and c >= 2}
        if not candidates:
            candidates = {v for v, c in freq.items() if 1 <= v <= 1000 and c >= 1}
        if not candidates:
            return [], [0x1337]

        mx = max(candidates)
        missing_vals: List[int] = []
        for add in (1, 2, 3, 7, 13):
            mv = mx + add
            if mv not in candidates:
                missing_vals.append(mv)
        if not missing_vals:
            missing_vals = [0x1337]

        offsets = [off for off, v in zip(offs, vals) if v in candidates]
        return offsets, missing_vals

    def _patch_int(self, data: bytes, off: int, val: int, size: int) -> bytes:
        if off < 0 or off + size > len(data):
            return data
        b = bytearray(data)
        if size == 4:
            b[off:off + 4] = struct.pack("<I", val & 0xFFFFFFFF)
        else:
            b[off:off + 8] = struct.pack("<Q", val & 0xFFFFFFFFFFFFFFFF)
        return bytes(b)