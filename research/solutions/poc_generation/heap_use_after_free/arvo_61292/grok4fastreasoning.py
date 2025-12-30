class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'FILE "a.wav" WAVE\nTRACK 01 AUDIO\n  INDEX 01 00:00:00\nTRACK 02 AUDIO\n  INDEX 01 00:01:00\nTRACK 03 AUDIO\n  INDEX 01 00:02:00\nTRACK 04 AUDIO\n  INDEX 01 00:03:00\n\n'
        return poc