class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"(class file (read))\n(macro m ((classpermission cp))\n  (classpermissionset s cp)\n)\n(call m ((cp (file (read)))))\n"
