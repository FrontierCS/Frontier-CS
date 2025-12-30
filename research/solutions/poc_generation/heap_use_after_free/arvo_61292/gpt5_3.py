import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        base = (
            'PERFORMER "A"\n'
            'TITLE "B"\n'
            'FILE "f.wav" WAVE\n'
            '  TRACK 01 AUDIO\n'
            '    INDEX 01 00:00:00\n'
            '  TRACK 02 AUDIO\n'
            '    INDEX 01 00:01:00\n'
        )
        target_len = 159
        s = base
        if len(s) < target_len:
            pad_len = target_len - len(s) - 5
            if pad_len < 0:
                pad_len = 0
            s += 'REM ' + ('X' * pad_len) + '\n'
        if len(s) < target_len:
            s += ' ' * (target_len - len(s))
        elif len(s) > target_len:
            s = s[:target_len]
        return s.encode('ascii', errors='ignore')