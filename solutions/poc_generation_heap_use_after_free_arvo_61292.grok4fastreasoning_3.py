class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'FILE "test.wav" WAVE\nTRACK 01 AUDIO\n  INDEX 01 00:00:00\n  INDEX 02 00:00:10\n  INDEX 03 00:00:20\n  INDEX 04 00:00:30\n  INDEX 05 00:00:40\n  INDEX 06 00:00:50\n  INDEX 07 00:01:00\n'
        return poc
