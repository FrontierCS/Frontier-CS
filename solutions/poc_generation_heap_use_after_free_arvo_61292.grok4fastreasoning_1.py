class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'''FILE "audiofile.bin" WAVE
PERFORMER "Artist"
TRACK 01 AUDIO
  INDEX 01 00:00:00
  INDEX 02 00:00:10
  INDEX 03 00:00:20
  INDEX 04 00:00:30
  INDEX 05 00:00:40
'''
        return poc
