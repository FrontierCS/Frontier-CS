import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        return (
            b'PERFORMER "X"\n'
            b'FILE "x" WAVE\n'
            b'TRACK 01 AUDIO\n'
            b'INDEX 01 00:00:00\n'
            b'TRACK 02 AUDIO\n'
            b'INDEX 01 00:01:00\n'
            b'TRACK 03 AUDIO\n'
            b'INDEX 01 00:02:00\n'
            b'TRACK 04 AUDIO\n'
            b'INDEX 01 00:03:00\n'
        )
