class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"function f(){var a=1n;a/=0n}try{f()}catch(e){}"
