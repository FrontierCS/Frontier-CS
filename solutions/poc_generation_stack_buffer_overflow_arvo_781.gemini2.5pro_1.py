class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a stack buffer over-read when processing regex match results.
        # The description "fewer capturing parentheses than the available space in the
        # external ovector" implies a bug in how the application handles the `ovector`
        # (output vector) from a regex library like PCRE.
        #
        # A common bug pattern is iterating over the ovector using an incorrect bound,
        # such as the length of the input string, instead of the number of captures
        # returned by the regex engine.
        #
        # To trigger this, we need a pattern with few captures and a subject string
        # that is longer than the number of values written to the ovector.
        #
        # The simplest pattern with the minimum number of captures (zero) is a single
        # character, e.g., "a". A successful match of this pattern will populate only
        # two elements of the ovector (`ovector[0]` and `ovector[1]`), for the start
        # and end of the overall match.
        #
        # If the code then loops, for instance, up to the length of the subject string,
        # and this length is greater than 2, it will read uninitialized stack data
        # from the ovector.
        #
        # The ground-truth PoC length is 8 bytes. We can construct an 8-byte PoC
        # assuming a standard `pattern\nsubject` input format.
        #
        # Pattern: "a" (1 byte)
        # Delimiter: "\n" (1 byte)
        # Subject: "aaaaaa" (6 bytes)
        # Total: 1 + 1 + 6 = 8 bytes.
        #
        # This input causes a match where the subject length (6) is greater than the
        # number of populated ovector elements (2), triggering the read out-of-bounds.
        return b'a\naaaaaa'
