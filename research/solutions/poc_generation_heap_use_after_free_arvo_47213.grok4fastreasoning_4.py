class Solution:
    def solve(self, src_path: str) -> bytes:
        N = 256
        arr = '[' + ','.join(map(str, range(N))) + ']'
        return arr.encode('ascii') + b'\n'