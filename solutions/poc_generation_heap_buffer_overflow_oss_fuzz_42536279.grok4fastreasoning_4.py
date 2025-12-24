class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_length = 6180
        poc = bytearray(poc_length)
        for i in range(poc_length):
            poc[i] = (i * 17) % 256  # Simple pattern to simulate fuzzed input
        # Prefix with a minimal HEVC-like start to potentially reach parsing
        poc[0:4] = b'\x00\x00\x01' + b'\x42'  # Example NAL start: SPS
        return bytes(poc)
