class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability in cJSON's parse_number function (oss-fuzz:42534949)
        # involves improper advancement of the pointer when handling a leading minus sign,
        # followed by an unsafe check for "Infinity" that can read out of bounds.
        # A short input like "[-Inf]" triggers this path:
        # 1. '-' causes pointer advancement.
        # 2. 'I' triggers the Infinity check.
        # 3. The check reads 8 bytes ("Infinity") but the buffer ends earlier, causing Stack Buffer Overflow (Read).
        return b'[-Inf]'
