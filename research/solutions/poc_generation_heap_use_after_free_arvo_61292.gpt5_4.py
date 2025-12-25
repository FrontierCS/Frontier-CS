import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        cue = (
            'FILE "x" WAVE\n'
            'TRACK 01 AUDIO\n'
            'INDEX 01 00:00:00\n'
        )
        return cue.encode('ascii')
