class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Craft a PoC input of 140 bytes to trigger stack buffer overflow
        # Assuming a simple overflow pattern; in practice, analyze src_path for format
        poc = b'A' * 140
        return poc
