import os
import re
import io
import tarfile
import zipfile
import tempfile
import struct
import zlib
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = os.path.join(td, "src")
            os.makedirs(root, exist_ok=True)
            self._extract_archive(src_path, root)

            fuzzer_files = self._find_fuzzer_sources(root)
            fmt_scores = self._score_formats(root, focus_files=fuzzer_files if fuzzer_files else None)

            samples = self._find_samples(root)
            chosen_fmt = self._choose_format(fmt_scores, samples)

            if chosen_fmt is None and samples:
                chosen_fmt = max(samples.items(), key=lambda kv: (kv[1][0], -kv[1][1], kv[0]))[0]  # count desc, size asc

            if chosen_fmt:
                patched = self._try_patch_sample(samples, chosen_fmt)
                if patched is not None:
                    return patched

            # Fallback: try patch any known sample irrespective of chosen format
            for fmt in ("gif", "png", "jpeg", "psd", "tiff", "bmp", "dds", "pnm"):
                patched = self._try_patch_sample(samples, fmt)
                if patched is not None:
                    return patched

            # Last resort: return a small crafted file (GIF then PNG)
            return self._minimal_gif_width0()

    def _extract_archive(self, src_path: str, out_dir: str) -> None:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.name or m.isdir():
                        continue
                    name = m.name
                    while name.startswith("./"):
                        name = name[2:]
                    if name.startswith("/") or ".." in name.split("/"):
                        continue
                    dest = os.path.normpath(os.path.join(out_dir, name))
                    if not dest.startswith(os.path.abspath(out_dir) + os.sep):
                        continue
                    parent = os.path.dirname(dest)
                    os.makedirs(parent, exist_ok=True)
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    with open(dest, "wb") as o:
                        o.write(f.read())
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    name = zi.filename
                    while name.startswith("./"):
                        name = name[2:]
                    if not name or name.startswith("/") or ".." in name.split("/"):
                        continue
                    dest = os.path.normpath(os.path.join(out_dir, name))
                    if not dest.startswith(os.path.abspath(out_dir) + os.sep):
                        continue
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with zf.open(zi, "r") as f, open(dest, "wb") as o:
                        o.write(f.read())
        else:
            # Assume already-extracted directory path
            if os.path.isdir(src_path):
                # Copy not needed; just point root to src_path by creating a symlink-like view is not possible.
                # We'll just walk src_path later by returning early; but caller expects out_dir populated.
                # So do a shallow copy of names (best effort).
                for dirpath, dirnames, filenames in os.walk(src_path):
                    rel = os.path.relpath(dirpath, src_path)
                    for fn in filenames:
                        sp = os.path.join(dirpath, fn)
                        try:
                            st = os.stat(sp)
                        except OSError:
                            continue
                        if st.st_size > 20_000_000:
                            continue
                        dp = os.path.join(out_dir, rel, fn) if rel != "." else os.path.join(out_dir, fn)
                        os.makedirs(os.path.dirname(dp), exist_ok=True)
                        try:
                            with open(sp, "rb") as f, open(dp, "wb") as o:
                                o.write(f.read())
                        except OSError:
                            continue

    def _iter_files(self, root: str) -> List[str]:
        res = []
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                res.append(p)
        return res

    def _find_fuzzer_sources(self, root: str) -> List[str]:
        fuzzer_files = []
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}
        for p in self._iter_files(root):
            ext = os.path.splitext(p)[1].lower()
            if ext not in exts:
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            if b"LLVMFuzzerTestOneInput" in b or b"LLVMFuzzerInitialize" in b:
                fuzzer_files.append(p)
        return fuzzer_files

    def _score_formats(self, root: str, focus_files: Optional[List[str]] = None) -> Dict[str, int]:
        keywords = {
            "gif": [
                ("gif_lib.h", 1000),
                ("dgif", 200),
                ("egif", 200),
                ("gif", 5),
                ("lzw", 20),
                ("gif89a", 200),
                ("gif87a", 200),
            ],
            "png": [
                ("<png.h", 1000),
                ("png.h", 500),
                ("libpng", 500),
                ("spng", 300),
                ("png_read", 200),
                ("png_sig_cmp", 300),
                ("ihdr", 50),
                ("idat", 50),
                ("ihex", 10),
            ],
            "jpeg": [
                ("jpeglib.h", 1000),
                ("libjpeg", 500),
                ("jpeg_", 100),
                ("jfif", 50),
                ("exif", 10),
            ],
            "tiff": [
                ("tiffio.h", 1000),
                ("libtiff", 500),
                ("tiff", 10),
                ("imagewidth", 50),
                ("imagelength", 50),
            ],
            "bmp": [
                ("bitmap", 40),
                ("bmp", 10),
                ("dib", 10),
            ],
            "psd": [
                ("psd", 50),
                ("8bps", 200),
                ("photoshop", 50),
            ],
            "dds": [
                ("dds", 50),
                ("dxt", 50),
                ("bc1", 50),
                ("bc7", 50),
            ],
            "webp": [
                ("webp", 80),
                ("vp8", 50),
                ("riff", 20),
                ("<webp/", 600),
                ("libwebp", 500),
            ],
            "jp2": [
                ("openjpeg", 600),
                ("jp2", 50),
                ("j2k", 50),
                ("jasper", 200),
            ],
            "exr": [
                ("openexr", 500),
                ("exr", 50),
                ("imf", 30),
            ],
            "pnm": [
                ("ppm", 30),
                ("pgm", 30),
                ("pbm", 30),
                ("pnm", 30),
                ("pam", 30),
                ("netpbm", 200),
            ],
        }

        name_keywords = {
            "gif": ["gif"],
            "png": ["png"],
            "jpeg": ["jpeg", "jpg"],
            "tiff": ["tiff", "tif"],
            "bmp": ["bmp", "bitmap"],
            "psd": ["psd"],
            "dds": ["dds"],
            "webp": ["webp", "vp8"],
            "jp2": ["jp2", "j2k", "openjpeg"],
            "exr": ["exr", "openexr"],
            "pnm": ["pnm", "ppm", "pgm", "pbm", "pam"],
        }

        scores: Dict[str, int] = {k: 0 for k in keywords.keys()}

        paths = focus_files if focus_files else self._iter_files(root)
        text_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl",
            ".py", ".sh", ".cmake", ".txt", ".md", ".rst", ".bazel", ".bzl",
            ".mk", ".mak", ".make", ".ac", ".am", ".in", ".yml", ".yaml", ".toml",
            ".java", ".kt", ".go", ".rs"
        }

        for p in paths:
            base = os.path.basename(p).lower()
            for fmt, nks in name_keywords.items():
                for nk in nks:
                    if nk in base:
                        scores[fmt] += 2

            ext = os.path.splitext(p)[1].lower()
            if ext not in text_exts:
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            if b"\x00" in b:
                continue
            low = b.decode("utf-8", errors="ignore").lower()

            for fmt, kws in keywords.items():
                for k, w in kws:
                    if k.startswith("<"):
                        if k in low:
                            scores[fmt] += w
                    else:
                        c = low.count(k)
                        if c:
                            scores[fmt] += min(2000, c) * w

            if "llvmfuzzertestoneinput" in low:
                # Extra emphasis for fuzzer files
                for fmt, kws in keywords.items():
                    for k, w in kws:
                        if k in low:
                            scores[fmt] += w * 3

        # Signature literals in sources
        sig_literals = {
            "gif": ["gif87a", "gif89a"],
            "png": ["\x89png", "ihdr", "idat"],
            "psd": ["8bps"],
            "dds": ["dds "],
            "tiff": ["ii*\x00", "mm\x00*"],
            "jpeg": ["\xff\xd8\xff", "jfif"],
            "webp": ["riff", "webp"],
        }
        for p in paths:
            ext = os.path.splitext(p)[1].lower()
            if ext not in text_exts:
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            low = b.decode("latin1", errors="ignore").lower()
            for fmt, lits in sig_literals.items():
                for lit in lits:
                    if lit in low:
                        scores[fmt] += 150

        return scores

    def _detect_magic_format(self, data: bytes) -> Optional[str]:
        if len(data) >= 6 and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return "gif"
        if len(data) >= 8 and data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if len(data) >= 2 and data[0:2] == b"\xff\xd8":
            return "jpeg"
        if len(data) >= 4 and data.startswith(b"8BPS"):
            return "psd"
        if len(data) >= 4 and data.startswith(b"DDS "):
            return "dds"
        if len(data) >= 4 and (data.startswith(b"II*\x00") or data.startswith(b"MM\x00*")):
            return "tiff"
        if len(data) >= 2 and data.startswith(b"BM"):
            return "bmp"
        if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "webp"
        if len(data) >= 4 and data[0:2] in (b"P1", b"P2", b"P3", b"P4", b"P5", b"P6", b"P7"):
            return "pnm"
        return None

    def _find_samples(self, root: str) -> Dict[str, Tuple[int, int, str]]:
        # format -> (count, min_size, min_path)
        best: Dict[str, Tuple[int, int, str]] = {}
        for p in self._iter_files(root):
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 5_000_000:
                continue
            ext = os.path.splitext(p)[1].lower()
            # likely binary candidates
            if ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".sh", ".txt", ".md", ".rst", ".cmake", ".json", ".xml", ".html"):
                continue
            try:
                with open(p, "rb") as f:
                    head = f.read(64)
            except OSError:
                continue
            fmt = self._detect_magic_format(head)
            if fmt is None:
                continue
            cnt, mn, mp = best.get(fmt, (0, 10**9, ""))
            cnt += 1
            if st.st_size < mn:
                mn = st.st_size
                mp = p
            best[fmt] = (cnt, mn, mp)
        return best

    def _choose_format(self, scores: Dict[str, int], samples: Dict[str, Tuple[int, int, str]]) -> Optional[str]:
        if not scores and samples:
            return max(samples.items(), key=lambda kv: (kv[1][0], -kv[1][1], kv[0]))[0]
        if scores:
            items = sorted(scores.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
            best_fmt, best_score = items[0]
            if best_score <= 0:
                if samples:
                    return max(samples.items(), key=lambda kv: (kv[1][0], -kv[1][1], kv[0]))[0]
                return None

            top = [kv for kv in items if kv[1] == best_score]
            if len(top) == 1:
                return best_fmt

            # tie-break with sample availability and count
            def tie_key(fmt: str) -> Tuple[int, int, int, str]:
                if fmt in samples:
                    cnt, mn, _ = samples[fmt]
                    return (1, cnt, -mn, fmt)
                return (0, 0, 0, fmt)

            return max([f for f, _ in top], key=tie_key)
        return None

    def _try_patch_sample(self, samples: Dict[str, Tuple[int, int, str]], fmt: str) -> Optional[bytes]:
        if fmt not in samples:
            return None
        _, _, path = samples[fmt]
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return None
        patched = self._patch_dims(data, fmt)
        return patched

    def _patch_dims(self, data: bytes, fmt: str) -> Optional[bytes]:
        if fmt == "gif":
            return self._patch_gif(data)
        if fmt == "png":
            return self._patch_png(data)
        if fmt == "jpeg":
            return self._patch_jpeg(data)
        if fmt == "bmp":
            return self._patch_bmp(data)
        if fmt == "psd":
            return self._patch_psd(data)
        if fmt == "dds":
            return self._patch_dds(data)
        if fmt == "tiff":
            return self._patch_tiff(data)
        if fmt == "pnm":
            return self._patch_pnm(data)
        return None

    def _patch_gif(self, data: bytes) -> Optional[bytes]:
        if len(data) < 13 or not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return None
        b = bytearray(data)
        packed = b[10]
        gct_flag = (packed & 0x80) != 0
        gct_sz = 0
        if gct_flag:
            gct_n = 1 << ((packed & 0x07) + 1)
            gct_sz = 3 * gct_n
        pos = 13 + gct_sz
        if pos >= len(b):
            return None

        # Find first image descriptor (0x2C) skipping extension blocks
        i = pos
        while i < len(b):
            c = b[i]
            if c == 0x2C:
                if i + 9 <= len(b):
                    # set image width to 0; keep height
                    b[i + 5] = 0
                    b[i + 6] = 0
                    return bytes(b)
                return None
            if c == 0x21:
                # extension: skip blocks
                if i + 2 >= len(b):
                    return None
                i += 2
                while i < len(b):
                    sz = b[i]
                    i += 1
                    if sz == 0:
                        break
                    i += sz
                continue
            if c == 0x3B:
                break
            i += 1
        # If no image descriptor found, patch LSD width to 0
        b[6:8] = b"\x00\x00"
        return bytes(b)

    def _patch_png(self, data: bytes) -> Optional[bytes]:
        if len(data) < 8 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        b = bytearray(data)
        off = 8
        while off + 12 <= len(b):
            ln = struct.unpack(">I", b[off:off + 4])[0]
            typ = bytes(b[off + 4:off + 8])
            if off + 12 + ln > len(b):
                break
            if typ == b'IHDR' and ln >= 13:
                data_off = off + 8
                # width (4) height (4)
                b[data_off:data_off + 4] = b"\x00\x00\x00\x00"
                # recompute crc
                chunk_data = bytes(b[off + 4: off + 8 + ln])
                crc = zlib.crc32(chunk_data) & 0xffffffff
                b[off + 8 + ln:off + 12 + ln] = struct.pack(">I", crc)
                return bytes(b)
            off += 12 + ln
        return None

    def _patch_jpeg(self, data: bytes) -> Optional[bytes]:
        if len(data) < 4 or data[0:2] != b"\xff\xd8":
            return None
        b = bytearray(data)
        i = 2
        sof_markers = set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)) | {0xDE}
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
            if marker == 0xD9 or marker == 0xDA:  # EOI or SOS
                break
            if marker == 0x01 or (0xD0 <= marker <= 0xD7):
                continue
            if i + 2 > len(b):
                break
            seglen = (b[i] << 8) | b[i + 1]
            if seglen < 2 or i + seglen > len(b):
                break
            if marker in sof_markers:
                # precision at i+2, height at i+3..4, width at i+5..6
                if seglen >= 7 and i + 7 <= len(b):
                    b[i + 5] = 0
                    b[i + 6] = 0
                    return bytes(b)
            i += seglen
        return None

    def _patch_bmp(self, data: bytes) -> Optional[bytes]:
        if len(data) < 26 or not data.startswith(b"BM"):
            return None
        b = bytearray(data)
        # DIB header starts at offset 14; width at 18, height at 22 for BITMAPINFOHEADER-style headers
        if len(b) >= 26:
            b[18:22] = b"\x00\x00\x00\x00"
            return bytes(b)
        return None

    def _patch_psd(self, data: bytes) -> Optional[bytes]:
        if len(data) < 26 or not data.startswith(b"8BPS"):
            return None
        b = bytearray(data)
        # width big-endian at offset 18
        b[18:22] = b"\x00\x00\x00\x00"
        return bytes(b)

    def _patch_dds(self, data: bytes) -> Optional[bytes]:
        if len(data) < 128 or not data.startswith(b"DDS "):
            return None
        b = bytearray(data)
        # width at offset 4+16; height at 4+12
        b[20:24] = b"\x00\x00\x00\x00"
        return bytes(b)

    def _patch_tiff(self, data: bytes) -> Optional[bytes]:
        if len(data) < 16 or not (data.startswith(b"II*\x00") or data.startswith(b"MM\x00*")):
            return None
        b = bytearray(data)
        le = b.startswith(b"II*\x00")
        def u16(off: int) -> int:
            if off + 2 > len(b):
                return 0
            return b[off] | (b[off + 1] << 8) if le else (b[off] << 8) | b[off + 1]
        def u32(off: int) -> int:
            if off + 4 > len(b):
                return 0
            if le:
                return b[off] | (b[off + 1] << 8) | (b[off + 2] << 16) | (b[off + 3] << 24)
            return (b[off] << 24) | (b[off + 1] << 16) | (b[off + 2] << 8) | b[off + 3]
        def p32(v: int) -> bytes:
            if le:
                return bytes((v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff))
            return bytes(((v >> 24) & 0xff, (v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff))

        ifd_off = u32(4)
        if ifd_off <= 0 or ifd_off + 2 > len(b):
            return None
        n = u16(ifd_off)
        ent = ifd_off + 2
        for _ in range(n):
            if ent + 12 > len(b):
                break
            tag = u16(ent)
            typ = u16(ent + 2)
            cnt = u32(ent + 4)
            val_off = ent + 8
            # Only handle simple inline LONG/SHORT with count=1
            if tag in (256, 257) and cnt == 1:
                if typ == 4:  # LONG
                    b[val_off:val_off + 4] = p32(0)
                elif typ == 3:  # SHORT, stored in first 2 bytes of value field
                    if le:
                        b[val_off:val_off + 2] = b"\x00\x00"
                    else:
                        b[val_off:val_off + 2] = b"\x00\x00"
            ent += 12
        return bytes(b)

    def _patch_pnm(self, data: bytes) -> Optional[bytes]:
        if len(data) < 3:
            return None
        if not (data.startswith(b"P1") or data.startswith(b"P2") or data.startswith(b"P3") or
                data.startswith(b"P4") or data.startswith(b"P5") or data.startswith(b"P6") or
                data.startswith(b"P7")):
            return None

        # For P1-P6: header tokens; for P7 PAM: key-value lines.
        if data.startswith(b"P7"):
            # Replace WIDTH value with 0 in PAM header.
            # Keep everything else.
            try:
                txt = data.decode("latin1", errors="ignore")
            except Exception:
                return None
            def repl(m):
                return m.group(1) + "0"
            new_txt = re.sub(r"(?im)^(width\s+)(\d+)\s*$", repl, txt, count=1)
            return new_txt.encode("latin1", errors="ignore")

        # P1-P6
        # Tokenize preserving whitespace; replace 2nd token after magic (width) with "0"
        s = data
        # find magic and then parse tokens
        i = 0
        if len(s) < 2:
            return None
        i = 2
        # skip whitespace/comments, then width token
        def skip_ws_and_comments(j: int) -> int:
            n = len(s)
            while j < n:
                c = s[j]
                if c in b" \t\r\n":
                    j += 1
                    continue
                if c == ord('#'):
                    while j < n and s[j] not in b"\r\n":
                        j += 1
                    continue
                break
            return j

        def read_token(j: int) -> Tuple[Optional[bytes], int]:
            n = len(s)
            j = skip_ws_and_comments(j)
            if j >= n:
                return None, j
            k = j
            while k < n and s[k] not in b" \t\r\n#":
                k += 1
            return s[j:k], k

        j = i
        width_tok, j2 = read_token(j)
        if width_tok is None:
            return None
        # locate exact slice to replace
        j = skip_ws_and_comments(j)
        start = j
        end = j2
        b = bytearray(s)
        b[start:end] = b"0"
        return bytes(b)

    def _minimal_gif_width0(self) -> bytes:
        # Minimal 1x1 GIF with image descriptor width patched to 0.
        # Based on a known minimal valid GIF; modifies image width field to 0.
        base = bytearray(
            b"GIF89a"
            b"\x01\x00\x01\x00"
            b"\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff"
            b"\x2c"
            b"\x00\x00\x00\x00"
            b"\x01\x00\x01\x00"
            b"\x00"
            b"\x02"
            b"\x02"
            b"\x44\x01"
            b"\x00"
            b"\x3b"
        )
        # image descriptor starts at 6+7+6=19? Actually fixed structure; width is at offset after 0x2c + 1+2+2 = 5 from descriptor.
        # Find 0x2c
        idx = base.find(b"\x2c")
        if idx != -1 and idx + 7 < len(base):
            base[idx + 5] = 0
            base[idx + 6] = 0
        return bytes(base)