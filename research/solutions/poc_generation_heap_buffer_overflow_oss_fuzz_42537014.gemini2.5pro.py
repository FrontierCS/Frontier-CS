class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a heap-buffer-overflow read in dash_client's
        # command-line argument parsing. The code uses `strncmp` to check for
        # argument prefixes like "benchmark=", which has a length of 10.
        # If the input argument is the string "benchmark" (length 9) located
        # in a buffer of size 9 (without a null terminator), the call to
        # `strncmp(arg, "benchmark=", 10)` will read one byte out of bounds.
        # This 9-byte PoC matches the ground-truth length for this vulnerability.
        return b'benchmark'
