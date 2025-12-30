class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'''(class a (x))
(macro m ((cp classpermissions))
(classpermissionset s $cp)
)
(m (a (x)))'''