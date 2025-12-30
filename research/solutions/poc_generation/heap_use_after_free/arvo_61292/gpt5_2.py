import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        return (
            b'REM GENRE Test\n'
            b'PERFORMER "X"\n'
            b'TITLE "Y"\n'
            b'FILE "a.wav" WAVE\n'
            b'  TRACK 01 AUDIO\n'
            b'    INDEX 01 00:00:00\n'
            b'  TRACK 02 AUDIO\n'
            b'    INDEX 00 00:30:00\n'
            b'    INDEX 01 00:32:00\n'
        )