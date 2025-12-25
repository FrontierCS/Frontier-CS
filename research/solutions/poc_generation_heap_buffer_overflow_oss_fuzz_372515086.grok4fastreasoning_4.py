class Solution:
    def solve(self, src_path: str) -> bytes:
        n = 204
        points = [b"0.0 0.0"] * n
        wkt = b"POLYGON((" + b", ".join(points) + b"))"
        return wkt
